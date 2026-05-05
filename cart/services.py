from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

from catalog.models import Product
from .models import Cart, CartItem, CartStatus
from order.services import OrderService


class CartService:
    # Cart TTL and extension in hours
    CART_TTL = timezone.timedelta(hours=168)
    CART_EXTENSION = timezone.timedelta(hours=12)
    CART_LOCK_TTL = timezone.timedelta(minutes=15)
    
    
    @staticmethod
    def _ensure_authenticated(user):
        if isinstance(user, AnonymousUser):
            raise ValueError("Signup required")
    
    
    @staticmethod
    @transaction.atomic
    def get_or_create_active_cart(user):
        CartService._ensure_authenticated(user=user)
        
        cart = (
            Cart.objects
            .select_for_update()
            .filter(user=user, status=CartStatus.ACTIVE)
            .first()
        )
        
        if cart and cart.expires_at < timezone.now():
            cart.status = CartStatus.EXPIRED
            cart.save(update_fields=["status"])
            cart = None
        
        if not cart:
            cart = Cart.objects.create(
                user=user,
                status=CartStatus.ACTIVE,
                expires_at=timezone.now() + CartService.CART_TTL
            )
        
        return cart
    
    
    @staticmethod
    def extend_cart_ttl(cart: Cart):
        cart.expires_at += CartService.CART_EXTENSION
        cart.save(update_fields=["expires_at"])

    
    @staticmethod
    def apply_coupon_to_cart(cart: Cart, coupon):
        from promotion.services import CouponService
        return CouponService.apply_coupon(cart, coupon)    
    
    
    @staticmethod
    def remove_coupon_from_cart(cart: Cart):
        from promotion.services import CouponService
        return CouponService.remove_coupon(cart=cart)
    
    
    @staticmethod
    def revalidate_cart_coupon(cart: Cart):
        from promotion.services import CouponService
        
        if not cart.coupon:
            return cart
        
        try:
            return CouponService.apply_coupon(
                cart=cart, 
                coupon=cart.coupon
            )
        except ValueError:
            return CouponService.remove_coupon(cart=cart)
    
    
    @staticmethod
    @transaction.atomic
    def add_to_cart(user, product_id, quantity):
        CartService._ensure_authenticated(user)
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        product = Product.objects.select_for_update().filter(id=product_id, is_active=True).first()
        
        if not product:
            raise ValueError("Product not found or inactive.")
        
        if quantity > product.quantity:
            raise ValueError("Insufficient stock")
        
        cart = CartService.get_or_create_active_cart(user)
        
        # Lock cart row
        cart = Cart.objects.select_for_update().get(id=cart.id)  
        
        cart_item, created = CartItem.objects.get_or_create( 
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                "price_snapshot": product.price
            }
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            
            if new_quantity > product.quantity:
                raise ValueError("Insufficient stock")
            
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=["quantity"])
            
        CartService.extend_cart_ttl(cart)
        CartService.revalidate_cart_coupon(cart)
        
        return cart
        
        
    @staticmethod
    @transaction.atomic
    def restore_cart(cart: Cart):
        cart = Cart.objects.select_for_update().get(id=cart.id)
        
        if cart.status != CartStatus.LOCKED:
            raise ValueError("Only locked cart can be restored")
        
        cart.status = CartStatus.ACTIVE
        cart.locked_at = None
        cart.save(update_fields=["status", "locked_at"])


    @staticmethod
    @transaction.atomic
    def update_cart_item(item, quantity):
        product = Product.objects.select_for_update().get(id=item.product_id)
        
        if quantity > product.quantity:
            raise ValueError("Insufficient stock")
        
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        
        cart = item.cart
        CartService.extend_cart_ttl(cart)
        CartService.revalidate_cart_coupon(cart)
        
        return cart
    
    
    @staticmethod
    @transaction.atomic
    def remove_cart_item(item):
        CartService._ensure_authenticated(item.cart__user)
        
        cart = item.cart
        item.delete()
        
        CartService.extend_cart_ttl(cart)
        CartService.revalidate_cart_coupon(cart)
        
        return cart
    
    
    @staticmethod
    @transaction.atomic
    def checkout_cart(user, address):
        CartService._ensure_authenticated(user)
        
        # Fetch active cart with row-level lock
        cart = (
            Cart.objects
            .select_for_update()
            .filter(user=user, status=CartStatus.ACTIVE)
            .first()
        )
        
        if not cart:
            raise ValueError("No active cart found.")
        
        if cart.expires_at < timezone.now():
            cart.status = CartStatus.EXPIRED
            cart.save(update_fields=["status"])
            raise ValueError("Cart expired")
        
        from promotion.services import CouponService
        CouponService.validate_before_checkout(user=user, cart=cart)
        
        # Lock cart items + products in one query
        items = list(
            cart.items
            .select_related("product")
            .select_for_update(of=("self", "product"))
        )
        
        # validate cart is not empty
        if not items:
            raise ValueError("Cart is empty")
        
        # Validate stock availability
        for item in items:
            if item.quantity > item.product.quantity:
                raise ValueError(f"Insufficient stock for {item.product.name}")
            
        # Lock cart
        cart.status = CartStatus.LOCKED
        cart.locked_at = timezone.now()
        cart.save(update_fields=["status", "locked_at"])
        
        # Create order from locked cart
        order = OrderService.create_order_from_cart(
            user=user,
            cart=cart,
            address=address
        )
        
        return {
            "order": order, 
            "cart": cart, 
        }
        
        