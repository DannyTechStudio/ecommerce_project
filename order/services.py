import uuid
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone

from accounts.models import Address
from .models import OrderStatus, Order, OrderItem
from cart.models import Cart, CartStatus

class OrderService:
    DEFAULT_CURRENCY = "GHS"
    
    @staticmethod
    def copy_shipping_snapshot(order: Order, address: Address):
        order.shipping_full_name = address.full_name
        order.shipping_line1 = getattr(address, "line1", "")
        order.shipping_line2 = getattr(address, "line2", "")
        order.shipping_street_address = getattr(address, "street_address", "")
        order.shipping_city = address.city
        order.shipping_state = address.state
        order.shipping_country = address.country
        order.shipping_postal_code = getattr(address, "postal_code", "")
        order.shipping_phone = getattr(address, "phone", "")
    
    
    @staticmethod
    def generate_order_number():
        return "ORD-" + uuid.uuid4().hex[:10].upper()
    
    
    @staticmethod
    def generate_unique_order_number():
        for _ in range(5):
            number = OrderService.generate_order_number()
            if not Order.objects.filter(order_number=number).exists():
                return number
        raise RuntimeError("Unable to generate unique order number")
    
    
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user, cart: Cart, address: Address):
        # Validate user address ownership
        if address.user != user:
            raise ValueError("Address does not belong to user")
        
        # Validate user cart ownership
        if cart.user != user:
            raise ValueError("Cart does not belong to user")
        
        # Validate cart status - locked
        if cart.status != CartStatus.LOCKED:
            raise ValueError("Cart must be locked before creating order")
        
        # Prevent duplicate order for the same cart
        if Order.objects.filter(cart=cart).exists():
            raise ValueError("Order already exists for this cart")
        
        # Obtain cart items
        items = list(
            cart.items
            .select_related("product")
            .only(
                "quantity",
                "price_snapshot",
                "product__id",
                "product__name"
            )
        )
        
        if not items:
            raise ValueError("Cannot checkout empty cart")
        
        # Compute total price using Decimal-safe accumulation
        total_price = sum(
            (item.quantity * item.price_snapshot for item in items),
            Decimal("0.00")
        )
        
        # Create order
        try:
            order = Order(
                order_number=OrderService.generate_unique_order_number(),
                user=user,
                cart=cart,
                status = OrderStatus.PENDING,
                total_price=total_price,
                currency=OrderService.DEFAULT_CURRENCY,
                shipping_address=address,
            )
        except IntegrityError:
            order = Order(
                order_number=OrderService.generate_unique_order_number(),
                user=user,
                cart=cart,
                status = OrderStatus.PENDING,
                total_price=total_price,
                currency=OrderService.DEFAULT_CURRENCY,
                shipping_address=address,
            )
            
        
        # Copy shipping snapshot fields
        OrderService.copy_shipping_snapshot(order, address)
        order.save()
        
        # Create order item snapshots
        order_items = [
            OrderItem(
                order=order,
                product_id=item.product.id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.price_snapshot,
                line_total=item.quantity * item.price_snapshot
            )
            for item in items
        ]
        
        OrderItem.objects.bulk_create(order_items)
        
        return order
    
    
    @staticmethod
    def cancel_order(order: Order):
        if order.status == OrderStatus.CANCELED:
            return order
        
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be canceled")
        
        order.status = OrderStatus.CANCELED
        order.save(update_fields=["status"])
        
        return order
        
            
    @staticmethod
    def mark_as_paid(order: Order):
        if order.status == OrderStatus.PAID:
            return order
        
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be marked as paid")
        
        order.status = OrderStatus.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        
        return order

    
    @staticmethod
    def mark_as_shipped(order: Order):
        if order.status != OrderStatus.PAID:
            raise ValueError("Only paid orders can be marked as shipped")
        
        order.status = OrderStatus.SHIPPED
        order.save(update_fields=["status"])
        
        return order

    
    @staticmethod
    def mark_as_delivered(order: Order):
        if order.status != OrderStatus.SHIPPED:
            raise ValueError("Only shipped orders can be marked as delivered")
        
        order.status = OrderStatus.DELIVERED
        order.save(update_fields=["status"])
        
        return order
    
    
    @staticmethod
    @transaction.atomic
    def pay_order(user, order_id, payment_method_id):
        order = (
            Order.objects
            .select_for_update()
            .select_related("cart")
            .get(id=order_id)
        )
        
        # Validate order belongs to the user
        if order.user != user:
            raise ValueError("Order does not belong to user")
        
        # Validate status
        if order.status != OrderStatus.PENDING:
            raise ValueError("Order cannot be paid")
        
        # Lazy import
        from payment.models import Payment, PaymentMethod
        
        # Check existing payment
        existing_payment = Payment.objects.filter(order=order).first()
        if existing_payment:
            if existing_payment.payment_url:
                return existing_payment         # reuse 
            else:
                existing_payment.delete()       # cleanup broken one
        
        # Fetch payment method
        payment_method = PaymentMethod.objects.get(
            id=payment_method_id,
            is_active = True
        )
        
        # Lazy import
        from payment.services import PaymentService
        
        # Create the payment
        payment = PaymentService.initiate_payment(
            order=order, 
            method=payment_method
        )
        
        return payment
        
        