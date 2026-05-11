from django.utils import timezone
from django.db.models import F

from order.models import Order, OrderStatus
from cart.models import Cart
from .models import Coupon, CouponDiscountTypeEnum


class CouponService:
    @staticmethod
    def get_coupon_by_code(code):
        return Coupon.objects.filter(
            code=code.strip().upper(), 
            is_active=True
        ).first()
    
    
    @staticmethod
    def validate_coupon(user, cart: Cart, coupon: Coupon):
        now = timezone.now()
        
        try:
            coupon = Coupon.objects.get(code=coupon)
        except Coupon.DoesNotExist:
            raise ValueError("Invalid coupon code")
        
        if coupon.is_active is not True:
            raise ValueError("Coupon is not active")
        
        if coupon.valid_from and now < coupon.valid_from:
            raise ValueError("Coupon is not valid yet")
        
        if coupon.valid_to and now > coupon.valid_to:
            raise ValueError("Coupon has expired")
        
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            raise ValueError("Coupon usage limit exceeded")
        
        if coupon.per_user_limit:
            user_usage_count = Cart.objects.filter(user=user, coupon=coupon).count()
            if user_usage_count >= coupon.per_user_limit:
                raise ValueError("You have already used this coupon the maximum number of times")
        
        subtotal = CouponService._calculate_subtotal(cart=cart)
        
        if coupon.min_order_value and subtotal < coupon.min_order_value:
            raise ValueError(f"Minimum order value of {coupon.min_order_value} not met for this coupon")
        
        if coupon.first_time_user_only and Order.objects.filter(user=user, status=OrderStatus.DELIVERED).exists():
            raise ValueError("Please this coupon is only for first-time customers")
        
        if not CouponService._is_applicable(cart, coupon):
            raise ValueError("Coupon is not applicable to any items in the cart")
    
        return coupon
        
    
    @staticmethod
    def apply_coupon(cart: Cart, coupon: Coupon):
        if cart.coupon:
            raise ValueError("A coupon has already been applied to this cart")
        
        CouponService.validate_coupon(cart.user, cart, coupon)
        
        discount = CouponService.calculate_discount(cart, coupon)
        
        cart.coupon = coupon
        cart.discount_amount = discount
        cart.save(update_fields=["coupon", "discount_amount"])
        
        return {
            "cart": cart,
            "detail": "Coupon added successfully"
        }


    @staticmethod
    def calculate_discount(cart: Cart, coupon: Coupon):
        subtotal = CouponService._calculate_subtotal(cart=cart)
        
        if coupon.discount_type == CouponDiscountTypeEnum.PERCENTAGE:
            discount = (subtotal * coupon.discount_value) / 100
        elif coupon.discount_type == CouponDiscountTypeEnum.FIXED:
            discount = coupon.discount_value
        else:
            discount = 0
            
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
        
        return min(discount, subtotal)


    @staticmethod
    def remove_coupon(cart: Cart):
        cart.coupon = None
        cart.discount_amount = 0
        cart.save(update_fields=["coupon", "discount_amount"])
        
        return {
            "cart": cart,
            "detail": "Coupon removed successfully",
        }
    
    
    @staticmethod
    def increment_coupon_usage(coupon: Coupon):
        Coupon.objects.filter(id=coupon.id).update(
            usage_count=F("usage_count") + 1
        )
    
    
    @staticmethod
    def validate_before_checkout(user, cart: Cart):
        if not cart.coupon:
            return cart
        
        try:
            CouponService.validate_coupon(user, cart, cart.coupon)
            return cart
        
        except ValueError:
            return CouponService.remove_coupon(cart)
    
    
    @staticmethod
    def get_applicable_coupon(user, cart: Cart):
        """
            suggests coupon to user
        """
        coupons = Coupon.objects.filter(is_active=True)
        
        for coupon in coupons:
            try:
                CouponService.validate_coupon(user, cart, coupon)
                return coupon
            except ValueError:
                continue
        
        return None
    
    
    @staticmethod
    def _calculate_subtotal(cart: Cart):
        return sum(
            item.quantity * item.price_snapshot for item in cart.items.all()
        )

    
    @staticmethod
    def _is_applicable(cart: Cart, coupon: Coupon):
        if not coupon.products.exists() and not coupon.categories.exists():
            return True
        
        for item in cart.items.select_related("product"):
            product = item.product
            
            if coupon.products.filter(id=product.id).exists():
                return True
            
            if coupon.categories.filter(id=product.category_id).exists():
                return True
        
        return False

