from django.db import transaction

from .models import WishList, WishListItem

from catalog.models import Product
from cart.models import CartItem
from cart.services import CartService


class WishListService:
    @staticmethod
    def _ensure_authenticated(user):
        if not user or not user.is_authenticated:
            raise ValueError("Signup required.")
        
    @staticmethod
    def _get_valid_product(product_id):
        product = Product.objects.filter(id=product_id, is_active=True).first()
        if not product:
            raise ValueError("Product not found or inactive.")
        
        return product
        
    
    @staticmethod
    def get_or_create_wishlist(user):
        WishListService._ensure_authenticated(user)
        wishlist, _ = WishList.objects.get_or_create(user=user)
            
        return wishlist
    
    
    @staticmethod
    def get_wishlist_items(user):
        WishListService._ensure_authenticated(user)
        wishlist = WishListService.get_or_create_wishlist(user)
        
        return wishlist.items.select_related("product")
    
    
    @staticmethod
    def get_wishlist_items_count(user):
        WishListService._ensure_authenticated(user)
        wishlist = WishListService.get_or_create_wishlist(user)
        
        return wishlist.items.count()
    
    
    @staticmethod
    def toggle_product(user, product_id):
        WishListService._ensure_authenticated(user)
        product = WishListService._get_valid_product(product_id)
        wishlist = WishListService.get_or_create_wishlist(user)
        
        item, created = WishListItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )
        
        if not created:
            item.delete()
            return {
                "status": "removed",
                "product_id": product.id
            }
        
        return {
            "status": "added",
            "product_id": product.id
        }


    @staticmethod
    def remove_wishlist_item(user, product_id):
        WishListService._ensure_authenticated(user)
        product = WishListService._get_valid_product(product_id)
        
        wishlist = WishListService.get_or_create_wishlist(user)
        
        deleted, _ = WishListItem.objects.filter(
            wishlist=wishlist,
            product=product
        ).delete()

        if not deleted:
            raise ValueError("Item not found in wishlist")
        
        return {
            "status": "removed",
            "product_id": product.id
        }
        

    @staticmethod
    def move_to_cart(user, product_id):
        WishListService._ensure_authenticated(user)
        product = WishListService._get_valid_product(product_id)
        
        cart = CartService.get_or_create_active_cart(user)
        wishlist = WishListService.get_or_create_wishlist(user)
        
        try:
            item = WishListItem.objects.get(
                wishlist=wishlist,
                product=product
            )
        except WishListItem.DoesNotExist:
            raise ValueError("Item not found in wishlist")
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": 1,
                "price_snapshot": product.price
            }
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save(update_fields=["quantity"])
        
        item.delete()
    
        return {
            "status": "moved_to_cart",
            "product": product.id
        }


    @staticmethod
    def move_all_to_cart(user):
        WishListService._ensure_authenticated(user)
        wishlist = WishListService.get_or_create_wishlist(user)
        cart = CartService.get_or_create_active_cart(user)
        
        with transaction.atomic():
            items = wishlist.items.select_related("product")

            for item in items:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=item.product,
                    defaults={
                        "quantity": 1,
                        "price_snapshot": item.product.price
                    }
                )
                
                if not created:
                    cart_item.quantity += 1
                    cart_item.save(update_fields=["quantity"])

            items.delete()
            
        return {"status": "moved_all_to_cart"}

