import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from app.forms import CheckoutForm, PaymentForm, SignUpForm, UpdateUserPersonalInfoForm
from app.models import Cart, CartItem, Messages, PaymentChoice, Product, ProductCategory, Room
from app.payments import (
    AUTOMATIC_PAYMENT_METHODS,
    confirm_payment_intent,
    get_or_create_customer,
    is_paid,
    needs_authentication,
    prepare_payment_intent,
    saved_card,
)
from app.utils import (
    accrual_bonus_coins,
    cart_data,
    get_session_key,
    pay_with_bonus_coins,
    save_cart_after_payment,
)

logger = logging.getLogger(__name__)


class SignUpView(FormView):
    template_name = "signup.html"
    form_class = SignUpForm
    success_url = "/login/"

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class UserPageView(LoginRequiredMixin, DetailView):
    template_name = "user-profile-page.html"

    def get_object(self, queryset=None):
        if self.request.user.default_card:
            return saved_card(self.request.user)


class UpdateUserPersonalInfoView(LoginRequiredMixin, UpdateView):
    template_name = "update-info.html"
    model = get_user_model()
    form_class = UpdateUserPersonalInfoForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return f'/{self.request.user.slug}/profile/'


class UserCardView(LoginRequiredMixin, TemplateView):
    template_name = 'user-card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        setup_intent = stripe.SetupIntent.create(
            customer=get_or_create_customer(user),
            automatic_payment_methods=AUTOMATIC_PAYMENT_METHODS,
            usage='on_session',
        )
        context.update(
            {
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
                'client_secret': setup_intent.client_secret,
                'card': saved_card(user),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except stripe.StripeError:
            logger.exception('Could not start card setup')
            messages.error(request, "Card service is unavailable. Please try again later.")
            return redirect(f'/{request.user.slug}/profile/')

    def post(self, request):
        user = request.user
        try:
            setup_intent = stripe.SetupIntent.retrieve(request.POST.get('setup_intent_id', ''))
            if setup_intent.customer != user.stripe_customer_id or setup_intent.status != 'succeeded':
                messages.error(request, "Card was not saved. Please try again.")
                return redirect('update_card')
            methods = stripe.Customer.list_payment_methods(user.stripe_customer_id, type='card')
            for method in methods.auto_paging_iter():
                if method.id != setup_intent.payment_method:
                    stripe.PaymentMethod.detach(method.id)
        except stripe.StripeError:
            logger.exception('Could not save card')
            messages.error(request, "Card was not saved. Please try again.")
            return redirect('update_card')
        user.default_card = True
        user.save(update_fields=['default_card'])
        return redirect(f'/{user.slug}/profile/')


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name = 'order-history.html'

    def get_queryset(self):
        return (
            Cart.objects.filter(user=self.request.user, ordered=True)
            .order_by('-ordered_date')
            .prefetch_related('items__item')
        )


class MainView(TemplateView):
    template_name = "main.html"


class CategoryView(TemplateView):
    template_name = "all-category-page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items_rating"] = Product.objects.all().order_by('-rating')[0:4]
        return context


class ProductView(ListView):
    template_name = "selected-category.html"

    def get_queryset(self):
        category = ProductCategory.objects.filter(slug=self.kwargs['slug']).first()
        return Product.objects.filter(category=category)


class SearchView(ListView):
    template_name = "search.html"
    paginate_by = 12

    def get_queryset(self):
        self.query = self.request.GET.get('q', '').strip()[:100]
        if not self.query:
            return Product.objects.none()
        return (
            Product.objects.filter(
                Q(title__icontains=self.query)
                | Q(compound__icontains=self.query)
                | Q(category__category__icontains=self.query)
            )
            .select_related('category')
            .order_by('-rating', 'title')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query
        return context


class ProductInfoView(DetailView):
    model = Product
    template_name = "detail-product-info.html"

    def get_queryset(self):
        return Product.objects.filter(category__slug=self.kwargs['category'])


class AddToCartView(View):
    def post(self, request):
        item = get_object_or_404(Product, id=request.POST['item_id'])
        cart = cart_data(request).first()
        if cart is None:
            cart = Cart.objects.create(
                session_key=get_session_key(request), user=request.user if request.user.is_authenticated else None
            )
            if not request.user.is_authenticated:
                request.session['cart_id'] = cart.id
        order_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
        if not created:
            order_item.quantity = F('quantity') + 1
            order_item.save(update_fields=['quantity'])
        return JsonResponse({'status': 'Added to cart'})


class DeleteElementFromCartView(View):
    def post(self, request):
        item = get_object_or_404(CartItem, id=request.POST['del_item'], cart__in=cart_data(request))
        item_on_delete = CartItem.objects.filter(id=item.id)
        item_on_delete.delete()
        if not cart_data(request).first().items.exists():
            cart_data(request).delete()
            return JsonResponse({})
        return JsonResponse({})


class DeleteAllElementsFromCartView(View):
    def post(self, request):
        cart = get_object_or_404(cart_data(request), id=request.POST['cart_id'])
        cart.items.all().delete()
        cart.delete()
        return JsonResponse({})


class CartView(TemplateView):
    template_name = "cart.html"


class CartRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET' and not cart_data(request).exists():
            return redirect('/cart/')
        return super().dispatch(request, *args, **kwargs)


class CheckoutView(CartRequiredMixin, TemplateView):
    template_name = 'checkout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'form': CheckoutForm(
                    initial={
                        'first_name': self.request.user.first_name if self.request.user.is_authenticated else None,
                        'last_name': self.request.user.last_name if self.request.user.is_authenticated else None,
                        'phone_number': self.request.user.phone_number if self.request.user.is_authenticated else None,
                        'address': self.request.user.address if self.request.user.is_authenticated else None,
                    }
                ),
            }
        )
        if (
            self.request.user.is_authenticated
            and self.request.user.bonus_coins >= cart_data(self.request).first().get_total()
        ):
            context['bonus_c'] = True
        return context

    def post(self, request):
        user = request.user
        form = CheckoutForm(cart_data(request), request.POST)
        if not form.is_valid():
            return self.form_invalid(form)

        payment_choice = form.cleaned_data['payment_choice']
        with transaction.atomic():
            cart = cart_data(request).select_for_update().first()
            if cart is None:
                return redirect('/cart/')
            if payment_choice == PaymentChoice.BONUS_COINS and not pay_with_bonus_coins(user, cart):
                form.add_error('payment_choice', 'Not enough bonus coins')
                return self.form_invalid(form)
            form.save()
            if payment_choice == PaymentChoice.CARD:
                return redirect('create-charge')
            if payment_choice == PaymentChoice.CASH:
                accrual_bonus_coins(user, cart)
            save_cart_after_payment(cart)
        return redirect('success')

    def form_invalid(self, form):
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class ChargeView(CartRequiredMixin, TemplateView):
    template_name = 'create-charge.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        card = saved_card(user) if user.is_authenticated and user.default_card else None
        return {'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY, 'card': card}

    def post(self, request):
        form = PaymentForm(request.POST)
        form.is_valid()
        user = request.user
        with transaction.atomic():
            cart = cart_data(request).select_for_update().first()
            if cart is None:
                return JsonResponse({'redirect': '/cart/'})

            if form.cleaned_data.get('use_default'):
                card = saved_card(user)
                payment_method = card['id'] if card else None
            else:
                payment_method = form.cleaned_data.get('payment_method_id')
            if not payment_method:
                return JsonResponse({'error': 'Please enter your card details.'}, status=400)

            return stripe_payment(
                user, cart, lambda: confirm_payment_intent(prepare_payment_intent(cart, user), payment_method)
            )


class ChargeConfirmView(View):
    def post(self, request):
        user = request.user
        with transaction.atomic():
            cart = cart_data(request).select_for_update().first()
            if cart is None:
                return JsonResponse({'redirect': '/cart/'})
            if not cart.stripe_payment_intent_id:
                return JsonResponse({'error': 'Payment not found. Please try again.'}, status=400)

            return stripe_payment(
                user,
                cart,
                lambda: stripe.PaymentIntent.retrieve(cart.stripe_payment_intent_id),
                allow_authentication=False,
            )


def stripe_payment(user, cart, pay, allow_authentication=True):
    try:
        intent = pay()
    except stripe.CardError as e:
        logger.info('Card declined: %s', e)
        return JsonResponse({'error': e.user_message or "Your card was declined."}, status=402)
    except stripe.InvalidRequestError as e:
        if e.code == 'amount_too_small':
            return JsonResponse(
                {'error': "Order total is too small for card payment. Please add more items or pay in cash."},
                status=400,
            )
        # Invalid parameters were supplied to Stripe's API
        logger.warning('Invalid Stripe request: %s', e)
        return JsonResponse({'error': "Invalid payment details."}, status=400)
    except stripe.AuthenticationError:
        # Authentication with Stripe's API failed
        logger.error('Stripe authentication failed')
        return JsonResponse({'error': "Payment service is unavailable."}, status=503)
    except stripe.StripeError:
        logger.exception('Stripe error')
        return JsonResponse({'error': "Something went wrong. You were not charged. Please try again."}, status=502)

    if needs_authentication(intent):
        if allow_authentication:
            return JsonResponse({'requires_action': True, 'client_secret': intent.client_secret})
        return JsonResponse({'error': "Card authentication was not completed. Please try again."}, status=402)
    if is_paid(intent, cart):
        accrual_bonus_coins(user, cart)
        save_cart_after_payment(cart)
        return JsonResponse({'redirect': '/success/'})
    if intent.status == 'succeeded':
        logger.error('PaymentIntent %s does not match cart %s', intent.id, cart.id)
        return JsonResponse({'error': "Payment does not match your order. Please contact support."}, status=409)
    return JsonResponse({'error': "Payment failed. Please try another card."}, status=402)


class SuccessView(TemplateView):
    template_name = 'success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_items'] = Product.objects.all().order_by('-added')[0:5]
        return context


class AboutUsView(TemplateView):
    template_name = 'about-us.html'


class RoomListView(ListView):
    template_name = 'room-list.html'

    def get_queryset(self):
        return Room.objects.all()


class TechSupportView(TemplateView):
    template_name = 'tech_support.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['room'] = get_object_or_404(Room, id=self.kwargs['room_name_id'])
        context['message'] = Messages.objects.filter(room_id=self.kwargs['room_name_id'])[:100]
        return context
