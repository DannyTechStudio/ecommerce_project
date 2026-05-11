from django.urls import path
from .views import (
    CartView,
    ApplyCouponView,
    RemoveCouponView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
    CheckoutCartView,
    
    # Admin views
    AdminCartListView,
    AdminUserCartHistoryView
)

urlpatterns = [
    path("", CartView.as_view(), name="cart-detail"),
    path("add/", AddToCartView.as_view(), name="cart-add"),
    path("coupon/apply/", ApplyCouponView.as_view(), name="apply-coupon"),
    path("coupon/remove/", RemoveCouponView.as_view(), name="remove-coupon"),
    path("items/<uuid:item_id>/update/", UpdateCartItemView.as_view(), name="cart-item-update"),
    path("items/<uuid:item_id>/remove/", RemoveCartItemView.as_view(), name="cart-item-remove"),
    path("checkout/", CheckoutCartView.as_view(), name="cart-checkout"),
    path("admin/carts/", AdminCartListView.as_view()),
    path("admin/users/<uuid:user_id>/carts/", AdminUserCartHistoryView.as_view()),
]
