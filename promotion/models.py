import uuid
from django.db import models

from catalog.models import Category, Product


# Coupon Discount Type Enum
class CouponDiscountTypeEnum(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED = 'fixed', 'Fixed Amount'


# Create your models here.
class Coupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=CouponDiscountTypeEnum.choices)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="coupons")
    categories = models.ManyToManyField(Category, blank=True, related_name="coupons")
    usage_limit = models.PositiveIntegerField(null=True, blank=True, default=0)
    usage_count = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    first_time_user_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.code









