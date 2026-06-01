"""
FastAPI Endpoints for Stripe Payment Integration
SPRINT 8 — Payment Flow Integration

Endpoints:
- GET /api/stripe-key → Frontend gets publishable key
- POST /api/payment-intent → Create Stripe PaymentIntent
- POST /api/payment-confirm → Confirm payment status
- POST /webhooks/stripe → Webhook for payment events
"""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
import stripe
import json
import hmac
import hashlib

from stripe_integration_adapter import (
    StripePaymentAdapter,
    PsychologicalPricingEngine
)

router = APIRouter(prefix="/api", tags=["payment"])

# Initialize Stripe
import os
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.get("/stripe-key")
async def get_stripe_key():
    """
    Return Stripe publishable key to frontend for Stripe.js initialization.
    """
    return {
        "publishableKey": StripePaymentAdapter.get_publishable_key()
    }


@router.get("/pricing")
async def get_pricing_context():
    """
    Return pricing cards context with psychological design principles.
    Frontend renders this data directly.
    """
    return PsychologicalPricingEngine.get_pricing_context()


@router.post("/payment-intent")
async def create_payment_intent(payload: dict):
    """
    Create Stripe PaymentIntent for checkout.

    Request body:
    {
        "couple_id": "session_abc123",
        "plan": "basic" | "premium",
        "user_email": "user@example.com",
        "analysis_data": {...}  # Full couple analysis
    }

    Response:
    {
        "client_secret": "pi_..._secret_...",
        "publishable_key": "pk_live_...",
        "intent_id": "pi_...",
        "amount": 1900 or 3900,
        "currency": "eur",
        "plan_name": "Reporte Básico" | "Plan de Élite"
    }
    """

    couple_id = payload.get("couple_id")
    plan = payload.get("plan")
    user_email = payload.get("user_email")
    analysis_data = payload.get("analysis_data", {})

    if not all([couple_id, plan, user_email]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: couple_id, plan, user_email"
        )

    if plan not in ["basic", "premium"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan: must be 'basic' or 'premium'"
        )

    try:
        intent_data = await StripePaymentAdapter.create_payment_intent(
            couple_id=couple_id,
            plan=plan,
            analysis_data=analysis_data,
            user_email=user_email
        )
        return intent_data

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment intent creation failed: {str(e)}"
        )


@router.post("/payment-confirm")
async def confirm_payment(payload: dict):
    """
    Confirm PaymentIntent after client-side Stripe.confirmPayment().

    Request body:
    {
        "intent_id": "pi_...",
        "couple_id": "session_abc123"
    }

    Response:
    {
        "success": true/false,
        "intent_id": "pi_...",
        "couple_id": "session_abc123",
        "status": "succeeded" | "processing" | "requires_payment_method",
        "magic_link": "https://...",
        "message": "..."
    }
    """

    intent_id = payload.get("intent_id")
    couple_id = payload.get("couple_id")

    if not all([intent_id, couple_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: intent_id, couple_id"
        )

    try:
        success, result = await StripePaymentAdapter.confirm_payment(
            intent_id=intent_id,
            couple_id=couple_id
        )

        return {
            "success": success,
            **result
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment confirmation failed: {str(e)}"
        )


@router.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    Signature verification required (Stripe sends X-Stripe-Signature header).

    Events handled:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - charge.refunded
    """

    try:
        payload = await request.body()
        sig_header = request.headers.get("X-Stripe-Signature")

        # Verify webhook signature
        if not sig_header or not STRIPE_WEBHOOK_SECRET:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Missing signature or webhook secret"}
            )

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid payload"}
            )
        except stripe.error.SignatureVerificationError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid signature"}
            )

        # Process event
        result = StripePaymentAdapter.handle_webhook(event)

        # Log event for analytics
        if event.get("type") == "payment_intent.succeeded":
            # TODO: Update couple record in database
            # TODO: Generate PDF if not already pre-rendered
            # TODO: Send success email with magic link
            pass

        elif event.get("type") == "payment_intent.payment_failed":
            # TODO: Send retry email with soft psychology
            pass

        elif event.get("type") == "charge.refunded":
            # TODO: Revoke PDF access, expire magic link
            pass

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Webhook processing failed: {str(e)}"}
        )


@router.get("/payment-status/{intent_id}")
async def get_payment_status(intent_id: str):
    """
    Poll payment status (optional, for checking status after payment attempt).

    Used by frontend for real-time status updates if needed.
    """

    try:
        intent = stripe.PaymentIntent.retrieve(intent_id)

        return {
            "intent_id": intent.id,
            "status": intent.status,
            "amount": intent.amount,
            "currency": intent.currency
        }

    except stripe.error.InvalidRequestError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment intent not found"
        )
