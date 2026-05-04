from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.db.models import F, Sum

from catalog.models import Product
from .models import Cart, CartItem, CartStatus
from promotion.services import CouponService

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
    def auto_restore_locked_cart(cart: Cart):
        if cart.status == CartStatus.LOCKED and cart.locked_at and cart.locked_at + CartService.CART_LOCK_TTL < timezone.now():
            cart.status = CartStatus.ACTIVE
            cart.locked_at = None
            cart.save(update_fields=["status", "locked_at"])
    
    
    @staticmethod
    @transaction.atomic
    def get_or_create_active_cart(user):
        """
            Returns active cart or creates a new one if expired or None
        """
        CartService._ensure_authenticated(user)
        
        cart = (
            Cart.objects
            .select_for_update()
            .filter(user=user, status=CartStatus.ACTIVE)
            .first()
        )
        
        # Expire cart if past TTL
        if cart and cart.expires_at < timezone.now():
            cart.status = CartStatus.EXPIRED
            cart.save(update_fields=["status"])
            cart = None
        
        # Create cart if None exsits and return as ACTIVE
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
    def lock_cart(cart: Cart):
        cart.status = CartStatus.LOCKED
        cart.locked_at = timezone.now()
        cart.save(update_fields=["status", "locked_at"])

        
    @staticmethod
    def expire_cart(cart: Cart):
        if cart.status != CartStatus.ACTIVE:
            raise ValueError("Cart not found or locked")
        
        if cart.expires_at < timezone.now():
            cart.status = CartStatus.EXPIRED
            cart.save(update_fields=["status"])
    
    
    @staticmethod
    def get_cart_subtotal(cart: Cart):
        result = CartItem.objects.filter(cart=cart).aggregate(
            subtotal=Sum(F("price_snapshot") * F("quantity"))
        )
        
        return result["subtotal"] or 0
    
    
    @staticmethod
    def get_cart_total(cart: Cart):
        subtotal = CartService.get_cart_subtotal(cart)
        discount = cart.discount_amount or 0
        return max(subtotal - discount, 0)
        
    
    @staticmethod
    def apply_coupon_to_cart(cart: Cart, coupon):
        discount_amount = CouponService.calculate_discount(cart, coupon)
        
        cart.coupon = coupon
        cart.discount_amount = discount_amount
        cart.save(update_fields=["coupon", "discount_amount"])
        
        return cart
    
    
    @staticmethod
    def remove_coupon_from_cart(cart: Cart):
        cart.coupon = None
        cart.discount_amount = 0
        cart.save(update_fields=["coupon", "discount_amount"])
        return cart
    
    
    @staticmethod
    def revalidate_cart_coupon(cart: Cart):
        if not cart.coupon:
            return cart
        try:
            CouponService.validate_coupon(
                user=cart.user, 
                cart=cart, 
                coupon=cart.coupon
            )
            return CartService.apply_coupon_to_cart(
                cart=cart, 
                coupon=cart.coupon
            )
        except ValueError:
            return CartService.remove_coupon_from_cart(cart)
    
    
    @staticmethod
    @transaction.atomic
    def add_to_cart(user, product_id, quantity):
        # Validates user is authenticated
        CartService._ensure_authenticated(user)
        
        # Validates quantity
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        # Get product with row-level lock
        product = Product.objects.select_for_update().filter(id=product_id, is_active=True).first()
        
        # Validates product exists
        if not product:
            raise ValueError("Product not found or inactive.")
        
        # Validate stock
        if quantity > product.quantity:
            raise ValueError("Insufficient stock available.")
        
        # Get or create active cart
        cart = CartService.get_or_create_active_cart(user)
        
        # Lock cart row
        cart = Cart.objects.select_for_update().get(id=cart.id)  
        
        # Create new cart item
        cart_item, created = CartItem.objects.get_or_create( 
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                "price_snapshot": product.price
            }
        )
        
        # if item exists increase its quantity
        if not created:
            new_quantity = cart_item.quantity + quantity
            
            if new_quantity > product.quantity:
                raise ValueError("Insufficient stock available.")
            
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=["quantity"])
            
        # Then extend cart time-to-live duration and return it
        CartService.extend_cart_ttl(cart)
        
        # Finally revalidate coupon if exists
        CartService.revalidate_cart_coupon(cart)
        
        return cart
    

    @staticmethod
    @transaction.atomic
    def consume_cart(cart: Cart):
        cart = Cart.objects.select_for_update().get(id=cart.id)
        
        if cart.status != CartStatus.LOCKED:
            raise ValueError("Only locked cart be consumed.")
        
        cart.status = CartStatus.CONSUMED
        cart.save(update_fields=["status"])
        
        
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
        
        # Validate cart exixts   
        if not cart:
            raise ValueError("No active cart found.")
        
        # Expiry check
        if cart.expires_at < timezone.now():
            cart.status = CartStatus.EXPIRED
            cart.save(update_fields=["status"])
            raise ValueError("Cart expired")
        
        # Revalidate coupon before checkout
        CartService.revalidate_cart_coupon(cart)
        
        # Lock cart items + products in one query
        items = list(
            cart.items
            .select_related("product")
            .select_for_update(of=("self", "product"))
        )
        
        # validate cart has items
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