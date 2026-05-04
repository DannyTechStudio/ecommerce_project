import uuid
from django.db import models
from django.conf import settings

from catalog.models import Product

User = settings.AUTH_USER_MODEL

# Cart Status Enum
class CartStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    LOCKED = "locked", "Locked"
    CONSUMED = "consumed", "Consumed"
    EXPIRED = "expired", "Expired"


# Create your models here.
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart")
    status = models.CharField(max_length=15, choices=CartStatus.choices, default=CartStatus.ACTIVE)
    locked_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    coupon = models.ForeignKey("promotion.Coupon", null=True, blank=True, on_delete=models.SET_NULL, related_name="carts")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(status=CartStatus.ACTIVE),
                name="unique_active_cart_per_user"
            )
        ]
    
    def __str__(self):
        return f"Cart: {self.id}, Status: {self.status}"
    

class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_item")
    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"CartItem: {self.id}, Quantity: {self.quantity}"
