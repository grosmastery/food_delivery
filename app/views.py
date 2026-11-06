import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from app.forms import CheckoutForm, PaymentForm, SignUpForm, UpdateUserPersonalInfoForm
from app.models import Cart, CartItem, Messages, PaymentChoice, Product, ProductCategory, Room
from app.utils import (
    accrual_bonus_coins,
    cart_data,
    get_session_key,
    pay_with_bonus_coins,
    save_cart_after_payment,
    stripe_amount,
    stripe_card,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


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
            # stripe_card - function from utils.py
            cards = stripe_card(self.request)
            return cards[0] if cards else None


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
        context['STRIPE_PUBLIC_KEY'] = settings.STRIPE_PUBLIC_KEY
        try:
            context.update({'card_list': stripe_card(self.request)})
            return context
        except TypeError:
            return context

    def post(self, request):
        user = request.user
        token = request.POST['stripeToken']
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f'{user.first_name} {user.last_name}',
                source=token,
            )
            user.stripe_customer_id = customer['id']
            user.default_card = True
            user.save()
        else:
            if stripe_card(request):
                stripe.Customer.delete_source(user.stripe_customer_id, stripe_card(request)[0]['id'])
            stripe.Customer.create_source(
                user.stripe_customer_id,
                source=token,
            )
            user.save()
        return redirect(f'/{request.user.slug}/profile/')


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name = 'order-history.html'

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user, ordered=True).prefetch_related('items')


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
        if not cart_data(request).exists():
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

        # if card was deleted by stipe platform
        try:
            card = stripe_card(self.request)[0] if user.is_authenticated and user.default_card else None
        except IndexError:
            card = None

        context = {'form': CheckoutForm, 'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY, 'card': card}
        return context

    def post(self, request):
        user = request.user
        form = PaymentForm(self.request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            use_default = form.cleaned_data.get('use_default')
            try:
                with transaction.atomic():
                    cart = cart_data(self.request).select_for_update().first()
                    if cart is None:
                        return redirect('/cart/')
                    if use_default:
                        stripe.Charge.create(
                            amount=stripe_amount(cart),
                            currency="uah",
                            customer=user.stripe_customer_id,
                            description=f'Order #{cart.id}',
                        )
                    else:
                        stripe.Charge.create(
                            amount=stripe_amount(cart),
                            currency="uah",
                            source=token,
                            description=f'Order #{cart.id}',
                        )
                    accrual_bonus_coins(user, cart)
                    save_cart_after_payment(cart)
                return redirect('/success/')

            except stripe.error.CardError as e:
                logger.info('Card declined: %s', e)
                body = e.json_body
                err = body.get('error', {})
                messages.error(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                logger.warning('Invalid Stripe request: %s', e)
                messages.error(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError:
                # Authentication with Stripe's API failed
                logger.error('Stripe authentication failed')
                messages.error(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.StripeError:
                logger.exception('Stripe error')
                messages.error(self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")


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
