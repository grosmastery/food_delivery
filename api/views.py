import json

from django.contrib.auth import get_user_model
from rest_framework import views, viewsets
from rest_framework.response import Response

from api.serializers import UserSerializer, ProductCategorySerializer, ProductSerializer, CreateProductSerializer, \
    CheckoutSerializer
from app.models import ProductCategory, Product, Cart
from app.utils import cart_data


class ProductCategoryApiView(views.APIView):

    @classmethod
    def get_extra_actions(cls):
        return []

    def get(self, request):
        serializer = ProductCategorySerializer(ProductCategory.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class ProductApiView(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    detail_serializer = ProductSerializer
    create_serializer = CreateProductSerializer
    queryset = Product.objects.all()

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in ['post', 'put', 'patch']:
            self.serializer_class = self.create_serializer
        return super(ProductApiView, self).dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        super(ProductApiView, self).update(request, *args, **kwargs)
        return Response(self.detail_serializer(self.get_object()).data)


class UserApiView(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = get_user_model().objects.all()


class CheckoutApiView(views.APIView):
    def get(self, request):
        serializer = CheckoutSerializer(cart_data(request), many=True)
        return Response({'checkout_user_cart': serializer.data})

    def post(self, request):
        serializer = CheckoutSerializer(cart_data(request), data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)
