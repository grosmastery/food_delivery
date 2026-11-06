from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from rest_framework.authtoken import views as drf_views
from rest_framework.routers import DefaultRouter

from api import views as api_views
from app import views

router = DefaultRouter()
router.register('users', api_views.UserApiView, basename='users')
router.register('categories', api_views.ProductCategoryApiView, basename='categories')
router.register('products', api_views.ProductApiView, basename='products')

urlpatterns = (
    [
        path('admin/', admin.site.urls),
        path('', views.MainView.as_view()),
        path('about-us/', views.AboutUsView.as_view()),
        path('tech/room-list/', views.RoomListView.as_view(), name='room_list'),
        path('tech-support/<int:room_name_id>/', views.TechSupportView.as_view(), name='room'),
        path('api/', include(router.urls)),
        path('api/categories/', api_views.ProductCategoryApiView.as_view()),
        path('api/checkout/', api_views.CheckoutApiView.as_view()),
        path('api-token-auth/', drf_views.obtain_auth_token),
        path('signup/', views.SignUpView.as_view(), name='signup'),
        path('login/', LoginView.as_view(template_name="login.html")),
        path('logout/', LogoutView.as_view()),
        path('<slug:slug>/profile/', views.UserPageView.as_view(), name='user_profile'),
        path('<slug:slug>/profile/update/', views.UpdateUserPersonalInfoView.as_view()),
        path('update-card/', views.UserCardView.as_view(), name='update_card'),
        path('<slug:slug>/profile/order-history/', views.OrderHistoryView.as_view()),
        path('category/', views.CategoryView.as_view()),
        path('category/<slug:slug>/', views.ProductView.as_view(), name='product_list'),
        path('category/<slug:category>/<slug:slug>/', views.ProductInfoView.as_view(), name='product_info'),
        path('add_to_cart/', views.AddToCartView.as_view(), name='add_to_cart'),
        path('del_element_from_cart/', views.DeleteElementFromCartView.as_view(), name='del_element_from_cart'),
        path(
            'del_all_elements_from_cart/',
            views.DeleteAllElementsFromCartView.as_view(),
            name='del_all_elements_from_cart',
        ),
        path('cart/', views.CartView.as_view()),
        path('checkout/', views.CheckoutView.as_view(), name='checkout'),
        path('create-charge/', views.ChargeView.as_view(), name='create-charge'),
        path('create-charge/confirm/', views.ChargeConfirmView.as_view(), name='confirm-charge'),
        path('success/', views.SuccessView.as_view(), name='success'),
    ]
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)

if settings.DEBUG:
    urlpatterns.append(
        path('__debug__/', include('debug_toolbar.urls')),
    )
