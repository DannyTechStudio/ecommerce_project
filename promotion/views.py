from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import Coupon
from .serializers import CouponSerializer, ApplyCouponSerializer
from .services import CouponService
# from cart.services import CartService


class CouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    

class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Preventing circular import        
        from cart.services import CartService
        
        code = serializer.validated_data["code"]
        cart = CartService.get_or_create_active_cart(request.user)
        coupon = CouponService.get_coupon_by_code(code)
        
        try:
            CouponService.validate_coupon(
                user=request.user,
                cart=cart,
                coupon=coupon
            )

            cart = CouponService.apply_coupon(cart, coupon)
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        cart.refresh_from_db()
        
        return Response(
            CouponSerializer(cart.coupon).data, 
            status=status.HTTP_200_OK
        )


class RemoveCouponView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        # Preventing circular import        
        from cart.services import CartService
        
        cart = CartService.get_or_create_active_cart(request.user)
        
        CouponService.remove_coupon(cart)
        
        return Response(
            {"detail": "Coupon removed successfully"},
            status=status.HTTP_200_OK
        )


class GetApplicableCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Preventing circular import        
        from cart.services import CartService
        
        cart = CartService.get_or_create_active_cart(request.user)
        
        coupon = CouponService.get_applicable_coupon(request.user, cart)
        
        if not coupon:
            return Response(
                {"detail": "No applicable coupons found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            CouponSerializer(coupon).data,
            status=status.HTTP_200_OK
        )


