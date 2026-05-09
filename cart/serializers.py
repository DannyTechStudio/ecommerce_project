from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "price",
            "quantity",
        ]
        
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            "id",
            "coupon",
            "status",
            "expires_at",
            "subtotal",
            "total",
            "items",
            "item_count",
        ]
        
    def get_subtotal(self, obj):
        return sum(
            item.quantity * item.price_snapshot for item in obj.items.all()
        )
        
    def get_total(self, obj):
        subtotal = self.get_subtotal(obj)
        total = subtotal - obj.discount_amount
        
        return total
        
    def get_item_count(self, obj):
        return obj.items.count()


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    
    def validate_code(self, value):
        return value.strip().upper()


class AddToCartSerializer(serializers.Serializer): 
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CheckoutResponseSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(source="order.id")
    order_number = serializers.CharField(source="order.order_number")
    cart_id = serializers.UUIDField(source="cart.id")