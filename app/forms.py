from django import forms
from django.contrib.auth import get_user_model

from app.models import Cart, PaymentChoice
from app.validators import is_valid_name, is_valid_phone_number
from app.widgets import ImageWidget


class UserFieldsValidationMixin(forms.ModelForm):
    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if is_valid_phone_number(phone_number):
            return phone_number
        else:
            raise forms.ValidationError("Invalid phone number")

    def clean_last_name(self):
        if not is_valid_name(self.cleaned_data['last_name']):
            raise forms.ValidationError("Invalid last name")
        else:
            return self.cleaned_data['last_name']

    def clean_first_name(self):
        if not is_valid_name(self.cleaned_data['first_name']):
            raise forms.ValidationError("Invalid first name")
        else:
            return self.cleaned_data['first_name']

    def clean_check_password(self):
        if self.cleaned_data["password"] != self.cleaned_data["check_password"]:
            raise forms.ValidationError("Invalid Password")
        else:
            return self.cleaned_data["password"]


class SignUpForm(UserFieldsValidationMixin):
    check_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = (
            "avatar",
            "email",
            "address",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "password",
            "check_password",
        )
        widgets = {"password": forms.widgets.PasswordInput(), 'avatar': ImageWidget()}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user


class UpdateUserPersonalInfoForm(UserFieldsValidationMixin):
    class Meta:
        model = get_user_model()
        fields = (
            "avatar",
            "address",
            "phone_number",
            "email",
            "username",
            "first_name",
            "last_name",
        )
        widgets = {'avatar': ImageWidget()}


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    use_default = forms.BooleanField(required=False)


class CheckoutForm(UserFieldsValidationMixin):
    payment_choice = forms.ChoiceField(widget=forms.RadioSelect, choices=PaymentChoice.choices, required=True)

    class Meta:
        model = Cart
        fields = ('description', 'first_name', 'last_name', 'phone_number', 'address')
        widgets = {
            'description': forms.widgets.Textarea(attrs={"cols": 30, "rows": 5}),
        }

    def __init__(self, cart=None, *args, **kwargs):
        self.cart = cart
        super().__init__(*args, **kwargs)

    def save(self, commit=True, *args, **kwargs):
        cart = super().save(commit=False)
        cart = self.cart
        cart.update(
            first_name=self.cleaned_data.get('first_name'),
            last_name=self.cleaned_data.get('last_name'),
            phone_number=self.cleaned_data.get('phone_number'),
            address=self.cleaned_data.get('address'),
            description=self.cleaned_data.get('description'),
            payment_choice=self.cleaned_data.get('payment_choice'),
        )
        return cart
