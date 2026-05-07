from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CouponViewSet,
    ApplyCouponView,
    RemoveCouponView,
    GetApplicableCouponView
)

router = DefaultRouter()
router.register("coupons", CouponViewSet, basename="coupon")

urlpatterns = [
    # User actions endpoints
    path("apply/", ApplyCouponView.as_view(), name="apply-coupon"),
    path("remove/", RemoveCouponView.as_view(), name="remove-coupon"),
    path("suggest/", GetApplicableCouponView.as_view(), name="suggest-coupon"),
    
    # Admin CRUD endpoints
    path("", include(router.urls)),
]