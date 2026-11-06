from django.contrib.auth import get_user_model
from rest_framework import status, views, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from api.permissions import IsAdminOrReadOnly
from api.serializers import (
    CheckoutSerializer,
    CreateProductSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    UserSerializer,
)
from app.models import Product, ProductCategory
from app.utils import cart_data


class ProductCategoryApiView(views.APIView):
    permission_classes = [IsAdminOrReadOnly]

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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductApiView(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    detail_serializer = ProductSerializer
    create_serializer = CreateProductSerializer
    queryset = Product.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in ['post', 'put', 'patch']:
            self.serializer_class = self.create_serializer
        return super().dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(self.detail_serializer(self.get_object()).data)


class UserApiView(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        users = get_user_model().objects.all()
        if self.request.user.is_staff:
            return users
        return users.filter(pk=self.request.user.pk)

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAdminUser()]
        return super().get_permissions()


class CheckoutApiView(views.APIView):
    def get(self, request):
        serializer = CheckoutSerializer(cart_data(request), many=True)
        return Response({'checkout_user_cart': serializer.data})

    def post(self, request):
        serializer = CheckoutSerializer(cart_data(request), data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
