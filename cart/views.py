from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.generics import ListAPIView

from accounts.models import Address
from promotion.services import CouponService
from .models import CartStatus, Cart, CartItem
from .services import CartService
from .serializers import CartSerializer, ApplyCouponSerializer, AddToCartSerializer, UpdateCartItemSerializer, CheckoutResponseSerializer

User = get_user_model()

# Create your views here.
class CartView(APIView):
    permission_classes = [IsAuthenticated]
    """ 
    Get current active cart or auto-create
    """
    def get(self, request):
        cart = CartService.get_or_create_active_cart(request.user)
        serializer = CartSerializer(cart)
        
        return Response(serializer.data)


class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data["code"]
        
        cart = CartService.get_or_create_active_cart(request.user)
        
        try:
            coupon = CouponService.validate_coupon(
                user=request.user,
                cart=cart,
                coupon=code
            )
            
            CartService.apply_coupon_to_cart(cart, coupon)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart.refresh_from_db()
        
        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK
        )
    
    
class RemoveCouponView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        cart = CartService.get_or_create_active_cart(request.user)
        
        try:
            CartService.remove_coupon_from_cart(cart)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
        # return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = CartService.add_to_cart(
            user=request.user,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"],
        )
        
        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK
        )
        
        
class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user,
            cart__status="ACTIVE",
        )
        
        try:
            cart = CartService.update_cart_item(
                item,
                serializer.validated_data["quantity"]
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(CartSerializer(cart).data)
    
    
class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user,
            cart__status=CartStatus.ACTIVE
        )
        
        try:
            cart = CartService.remove_cart_item(item)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_204_NO_CONTENT
        )
        
        
class CheckoutCartView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        address_id = request.data.get("address_id")
        
        if not address_id:
            return Response(
                {"detail": "Address ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user
        )
        
        try:
            result = CartService.checkout_cart(
                user=request.user,
                address=address
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                {"detail": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        serializer = CheckoutResponseSerializer(result)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
        
# Admin views
class AdminCartListView(ListAPIView):
    """
        Admin: view all carts in the system, sorted by date created and status 
    """
    permission_classes = [IsAdminUser]
    serializer_class = CartSerializer
    
    def get_queryset(self):
        return Cart.objects.all().order_by("-created_at", "status")

    
class AdminUserCartHistoryView(ListAPIView):
    """
        Admin: view all carts of a specific user including active and past carts 
    """
    permission_classes = [IsAdminUser]
    serializer_class = CartSerializer
    
    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        user = get_object_or_404(User, id=user_id)
        
        return (
            Cart.objects
            .filter(user=user)
            .select_related("user")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )