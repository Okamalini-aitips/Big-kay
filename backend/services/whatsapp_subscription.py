"""WhatsApp Group Subscription Service for OkaMoney AI Tips

Manages WhatsApp group subscriptions.
- R125/month for WhatsApp group access
- Purchase windows only open on 8th and 26th of each month
- Generates downloadable receipt as proof of payment

Uses MongoDB for persistent storage.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)

# WhatsApp subscription price
WHATSAPP_GROUP_PRICE = 125  # R125

# Purchase window days (8th and 26th of each month)
PURCHASE_WINDOW_DAYS = [8, 26]


class WhatsAppSubscriptionService:
    """Manages WhatsApp group subscriptions with MongoDB storage."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.subscriptions = db.whatsapp_subscriptions
    
    async def initialize(self):
        """Create indexes for the collections."""
        await self.subscriptions.create_index("receipt_id", unique=True)
        await self.subscriptions.create_index("user_id")
        await self.subscriptions.create_index("created_at")
        logger.info("WhatsApp subscription service initialized with indexes")
    
    def is_purchase_window_open(self) -> Dict:
        """Check if the purchase window is currently open."""
        now = datetime.now()
        current_day = now.day
        current_month = now.month
        current_year = now.year
        
        is_open = current_day in PURCHASE_WINDOW_DAYS
        
        if is_open:
            next_window = now
            window_closes = now.replace(hour=23, minute=59, second=59)
        else:
            next_window_day = None
            next_month = current_month
            next_year = current_year
            
            for day in PURCHASE_WINDOW_DAYS:
                if day > current_day:
                    next_window_day = day
                    break
            
            if next_window_day is None:
                next_window_day = PURCHASE_WINDOW_DAYS[0]
                next_month = current_month + 1
                if next_month > 12:
                    next_month = 1
                    next_year = current_year + 1
            
            try:
                next_window = datetime(next_year, next_month, next_window_day, 0, 0, 0)
            except ValueError:
                next_window = datetime(next_year, next_month, min(next_window_day, 28), 0, 0, 0)
            
            window_closes = None
        
        if not is_open:
            time_until = next_window - now
            days_until = time_until.days
            hours_until = time_until.seconds // 3600
            minutes_until = (time_until.seconds % 3600) // 60
        else:
            days_until = 0
            hours_until = 0
            minutes_until = 0
        
        return {
            "is_open": is_open,
            "current_day": current_day,
            "purchase_days": PURCHASE_WINDOW_DAYS,
            "next_window": next_window.strftime("%Y-%m-%d") if not is_open else None,
            "next_window_formatted": next_window.strftime("%d %B %Y") if not is_open else None,
            "countdown": {
                "days": days_until,
                "hours": hours_until,
                "minutes": minutes_until
            } if not is_open else None,
            "window_closes": window_closes.isoformat() if window_closes else None,
            "price": WHATSAPP_GROUP_PRICE
        }
    
    async def purchase_subscription(self, user_id: str, user_name: str = "User", user_email: str = None) -> Dict:
        """Purchase WhatsApp group subscription."""
        window_status = self.is_purchase_window_open()
        if not window_status["is_open"]:
            return {
                "success": False,
                "error": "Purchase window is closed",
                "next_window": window_status["next_window_formatted"],
                "countdown": window_status["countdown"]
            }
        
        now = datetime.now()
        receipt_id = f"WA-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        group_start = now.strftime("%d %B %Y")
        
        if now.day == 8:
            expiry_day = 9
        else:
            expiry_day = 27
        
        next_month = now.month + 1
        next_year = now.year
        if next_month > 12:
            next_month = 1
            next_year = now.year + 1
        
        try:
            expiry_date = datetime(next_year, next_month, expiry_day)
        except ValueError:
            expiry_date = datetime(next_year, next_month, min(expiry_day, 28))
        
        subscription_doc = {
            "receipt_id": receipt_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "amount": WHATSAPP_GROUP_PRICE,
            "currency": "ZAR",
            "purchase_date": now,
            "group_start_date": group_start,
            "valid_until": expiry_date,
            "status": "paid",
            "verified": False,
            "verified_at": None,
            "created_at": now
        }
        
        await self.subscriptions.insert_one(subscription_doc)
        
        receipt_data = {
            "receipt_id": receipt_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "product": "OkaMoney WhatsApp Group Subscription",
            "amount": WHATSAPP_GROUP_PRICE,
            "currency": "ZAR",
            "purchase_date": now.strftime("%d %B %Y"),
            "purchase_time": now.strftime("%H:%M"),
            "purchase_timestamp": now.isoformat(),
            "group_start_date": group_start,
            "valid_until": expiry_date.strftime("%d %B %Y"),
            "status": "PAID",
            "payment_method": "In-App Payment",
            "instructions": [
                "1. Download or screenshot this receipt",
                "2. Send this receipt to our WhatsApp: +27 72 517 7829",
                "3. You will be verified and added to the group",
                "4. Start receiving 2-4 daily betslips @ 1.90-5.50 odds"
            ]
        }
        
        return {
            "success": True,
            "receipt": receipt_data,
            "message": "Payment successful! Please send your receipt to WhatsApp to join the group."
        }
    
    async def get_receipt(self, receipt_id: str) -> Optional[Dict]:
        """Get a specific receipt by ID."""
        sub = await self.subscriptions.find_one({"receipt_id": receipt_id})
        if not sub:
            return None
        
        sub['id'] = str(sub.pop('_id'))
        if 'purchase_date' in sub and sub['purchase_date']:
            sub['purchase_date'] = sub['purchase_date'].isoformat()
        if 'valid_until' in sub and sub['valid_until']:
            sub['valid_until'] = sub['valid_until'].isoformat()
        if 'created_at' in sub and sub['created_at']:
            sub['created_at'] = sub['created_at'].isoformat()
        
        return sub
    
    async def get_user_subscriptions(self, user_id: str) -> List[Dict]:
        """Get all subscriptions for a user."""
        cursor = self.subscriptions.find({"user_id": user_id}).sort("created_at", -1)
        
        subs = []
        async for sub in cursor:
            sub['id'] = str(sub.pop('_id'))
            if 'purchase_date' in sub and sub['purchase_date']:
                sub['purchase_date'] = sub['purchase_date'].isoformat()
            if 'valid_until' in sub and sub['valid_until']:
                sub['valid_until'] = sub['valid_until'].isoformat()
            subs.append(sub)
        
        return subs
    
    async def verify_receipt(self, receipt_id: str) -> Dict:
        """Verify a receipt ID for admin verification."""
        sub = await self.subscriptions.find_one({"receipt_id": receipt_id})
        
        if not sub:
            return {
                "valid": False,
                "error": "Receipt not found - may be invalid or forged"
            }
        
        return {
            "valid": True,
            "already_verified": sub.get("verified", False),
            "verified_at": sub.get("verified_at").isoformat() if sub.get("verified_at") else None,
            "receipt": {
                "receipt_id": sub.get("receipt_id"),
                "user_name": sub.get("user_name"),
                "user_email": sub.get("user_email"),
                "amount": sub.get("amount"),
                "purchase_date": sub.get("purchase_date").isoformat() if sub.get("purchase_date") else None,
                "valid_until": sub.get("valid_until").isoformat() if sub.get("valid_until") else None,
                "status": sub.get("status")
            }
        }
    
    async def mark_as_verified(self, receipt_id: str) -> Dict:
        """Mark a receipt as verified (user added to group)."""
        sub = await self.subscriptions.find_one({"receipt_id": receipt_id})
        
        if not sub:
            return {"success": False, "error": "Receipt not found"}
        
        if sub.get("verified", False):
            return {
                "success": False,
                "error": "Receipt already verified",
                "verified_at": sub.get("verified_at").isoformat() if sub.get("verified_at") else None
            }
        
        verified_at = datetime.now()
        await self.subscriptions.update_one(
            {"receipt_id": receipt_id},
            {"$set": {"verified": True, "verified_at": verified_at}}
        )
        
        return {
            "success": True,
            "message": "Receipt marked as verified",
            "receipt_id": receipt_id,
            "user_name": sub.get("user_name"),
            "verified_at": verified_at.isoformat()
        }
    
    async def get_all_subscriptions(self, include_verified: bool = True) -> List[Dict]:
        """Get all subscriptions (for admin view)."""
        query = {} if include_verified else {"verified": {"$ne": True}}
        cursor = self.subscriptions.find(query).sort("created_at", -1)
        
        subs = []
        async for sub in cursor:
            sub['id'] = str(sub.pop('_id'))
            if 'purchase_date' in sub and sub['purchase_date']:
                sub['purchase_date'] = sub['purchase_date'].isoformat()
            if 'valid_until' in sub and sub['valid_until']:
                sub['valid_until'] = sub['valid_until'].isoformat()
            if 'verified_at' in sub and sub['verified_at']:
                sub['verified_at'] = sub['verified_at'].isoformat()
            subs.append(sub)
        
        return subs


# Singleton
_whatsapp_service = None


def get_whatsapp_service(db: AsyncIOMotorDatabase = None) -> WhatsAppSubscriptionService:
    """Get or create the WhatsApp subscription service singleton."""
    global _whatsapp_service
    if _whatsapp_service is None and db is not None:
        _whatsapp_service = WhatsAppSubscriptionService(db)
    return _whatsapp_service
