# payments.py
import os
import razorpay
from uuid import uuid4

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

def create_payment_link(user_id: int):
    """Creates a Razorpay payment link for ₹79 Lifetime."""
    try:
        link = client.payment_link.create({
            "amount": 7900,  # Amount in paise (7900 = ₹79.00)
            "currency": "INR",
            "accept_partial": False,
            "description": "UOR Job Bot - Lifetime Premium",
            "customer": {
                "email": f"user_{user_id}@uorjob.bot"
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {
                "telegram_user_id": str(user_id) # CRITICAL: To identify the user later
            },
            "callback_url": "https://t.me/UORJOB_bot", # CHANGE THIS
            "callback_method": "get"
        })
        return link.get('short_url')
    except Exception as e:
        print(f"Error creating payment link: {e}")
        return None