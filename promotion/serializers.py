from rest_framework import serializers

from .models import Coupon, CouponDiscountTypeEnum
from catalog.models import Category, Product


class CouponSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True, 
        required=False
    )
    
    categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True, 
        required=False
    )
        
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",    
            "max_discount_amount",
            "min_order_value",
            "products",
            "categories",
            "usage_limit",
            "usage_count",
            "per_user_limit",
            "first_time_user_only",
            "is_active",
            "valid_from",
            "valid_to",
        ]
        
        def validate(self, data):
            if data["discount_value"] <= 0:
                raise serializers.ValidationError("Discount must be greater than zero")

            if (data["discount_type"] == CouponDiscountTypeEnum.PERCENTAGE 
                and data["discount_value"] > 100):
                raise serializers.ValidationError("Percentage discount cannot exceed 100")
            
            if data["valid_from"] >= data["valid_to"]:
                raise serializers.ValidationError("Invalid validity period")
            
            return data

        
class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    
    def validate_code(self, value):
        return value.strip().upper()
    
