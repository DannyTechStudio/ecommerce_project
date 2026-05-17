import json
import hmac
import hashlib
import logging

from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from .models import Payment, PaymentEvent, PaymentStatus
from .services import PaymentService
from order.models import OrderStatus

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class PayStackWebhookView(View):
    def post(self, request):
        logger.info("Webhook endpoint hit")
        
        payload = request.body
        
        signature = (
            request.headers.get("x-paystack-signature")
            or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
        )
        
        computed_hash = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        if not hmac.compare_digest(signature or "", computed_hash):
            logger.warning("Invalid webhook signature")
            return HttpResponse(status=400)
        
        data = json.loads(payload)
        event = data.get("event")
        reference = data.get("data", {}).get("reference")
        
        logger.info(f"Webhook event received: {event}, Ref: {reference}")
        
        payment = Payment.objects.filter(reference=reference).first()
            
        if not payment:
            logger.warning(f"No payment found for reference: {reference}")
            
            verification = PaymentService.verify_payment(reference=reference)
            
            if verification:
                logger.info("Recovered payment via provider")
                
            return HttpResponse(status=200)
        
        if payment.status == PaymentStatus.SUCCESS:
            return HttpResponse(status=200)
            
        # store event
        PaymentEvent.objects.create(
            payment=payment,
            event_type=event,
            payload=data
        )
        
        # Handle successful payment
        if event == "charge.success":
            payment.status = PaymentStatus.SUCCESS
            payment.save()
            
            order = payment.order
            order.status = OrderStatus.PAID
            order.save()
            
        return HttpResponse(status=200)

