from django.contrib import admin
from .models import Coupon

# Register your models here.
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code", 
        "discount_type", 
        "max_discount_amount", 
        "min_order_value", 
        "usage_limit", 
        "usage_count", 
        "per_user_limit", 
        "first_time_user_only", 
        "is_active", "valid_from", 
        "valid_to",
        "get_products",
        "get_categories",
    )
    
    list_filter = ["is_active", "discount_type", "valid_from", "valid_to"]
    search_fields = ["code"]
    ordering = ["-created_at"]
    
    filter_horizontal = ["products", "categories"]

    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=Coupon):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_products(self, obj):
        return ", ".join([p.name for p in obj.products.all()[:3]])
    get_products.short_description = "Products"
    
    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()[:3]])
    get_categories.short_description = "Categories" 
 
