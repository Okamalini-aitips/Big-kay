"""Push Notification Service for Daily Picks"""
import logging
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushNotificationService:
    """Handle Expo push notifications for daily picks"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tokens_collection = db.push_tokens
    
    async def register_token(self, token: str, device_info: Dict = None) -> Dict:
        """
        Register or update a push notification token
        
        Args:
            token: Expo push token (ExponentPushToken[...])
            device_info: Optional device information
        """
        if not token or not token.startswith("ExponentPushToken"):
            logger.warning(f"Invalid push token format: {token}")
            return {"success": False, "error": "Invalid token format"}
        
        now = datetime.utcnow()
        
        # Check if token exists
        existing = await self.tokens_collection.find_one({"token": token})
        
        if existing:
            # Update last seen
            await self.tokens_collection.update_one(
                {"token": token},
                {"$set": {"last_seen": now, "device_info": device_info}}
            )
            logger.info(f"Updated existing push token: {token[:30]}...")
        else:
            # Insert new token
            await self.tokens_collection.insert_one({
                "token": token,
                "created_at": now,
                "last_seen": now,
                "device_info": device_info,
                "active": True
            })
            logger.info(f"Registered new push token: {token[:30]}...")
        
        return {"success": True, "token": token}
    
    async def unregister_token(self, token: str) -> Dict:
        """Unregister a push token"""
        result = await self.tokens_collection.update_one(
            {"token": token},
            {"$set": {"active": False}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Unregistered push token: {token[:30]}...")
            return {"success": True}
        
        return {"success": False, "error": "Token not found"}
    
    async def get_active_tokens(self) -> List[str]:
        """Get all active push tokens"""
        cursor = self.tokens_collection.find({"active": True})
        tokens = await cursor.to_list(length=1000)
        return [t["token"] for t in tokens]
    
    async def send_notification(self, token: str, title: str, body: str, 
                                 data: Dict = None) -> Dict:
        """
        Send a push notification to a single device
        
        Args:
            token: Expo push token
            title: Notification title
            body: Notification body
            data: Additional data payload
        """
        message = {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
            "data": data or {},
            "priority": "high",
            "channelId": "daily-picks"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=message,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    logger.info(f"Notification sent successfully to {token[:30]}...")
                    return {"success": True, "result": result}
                else:
                    logger.error(f"Failed to send notification: {result}")
                    return {"success": False, "error": result}
                    
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_bulk_notifications(self, title: str, body: str, 
                                       data: Dict = None) -> Dict:
        """
        Send notifications to all active tokens
        
        Args:
            title: Notification title
            body: Notification body
            data: Additional data payload
        """
        tokens = await self.get_active_tokens()
        
        if not tokens:
            logger.warning("No active push tokens found")
            return {"success": False, "error": "No active tokens", "sent": 0}
        
        logger.info(f"Sending notifications to {len(tokens)} devices...")
        
        # Expo allows batches of up to 100 notifications
        messages = []
        for token in tokens:
            messages.append({
                "to": token,
                "sound": "default",
                "title": title,
                "body": body,
                "data": data or {},
                "priority": "high",
                "channelId": "daily-picks"
            })
        
        # Send in batches of 100
        sent = 0
        failed = 0
        
        try:
            async with httpx.AsyncClient() as client:
                for i in range(0, len(messages), 100):
                    batch = messages[i:i+100]
                    
                    response = await client.post(
                        EXPO_PUSH_URL,
                        json=batch,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json"
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        # Count successes and failures
                        for ticket in result.get("data", []):
                            if ticket.get("status") == "ok":
                                sent += 1
                            else:
                                failed += 1
                                # Mark invalid tokens as inactive
                                if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                                    token_index = result["data"].index(ticket)
                                    if token_index < len(batch):
                                        await self.unregister_token(batch[token_index]["to"])
                    else:
                        failed += len(batch)
                        logger.error(f"Batch send failed: {response.text}")
            
            logger.info(f"Bulk notification complete: {sent} sent, {failed} failed")
            return {"success": True, "sent": sent, "failed": failed, "total": len(tokens)}
            
        except Exception as e:
            logger.error(f"Error sending bulk notifications: {e}")
            return {"success": False, "error": str(e), "sent": sent, "failed": failed}
    
    async def send_daily_picks_notification(self, picks: List[Dict]) -> Dict:
        """
        Send the daily picks notification
        
        Args:
            picks: List of today's picks
        """
        if not picks:
            logger.warning("No picks to notify about")
            return {"success": False, "error": "No picks available"}
        
        # Count by market type
        dc_count = len([p for p in picks if p.get('market', {}).get('type') == 'DC_U4.5'])
        btts_count = len([p for p in picks if p.get('market', {}).get('type') == '1X2_BTTS'])
        corners_count = len([p for p in picks if p.get('market', {}).get('type') == 'TEAM_1H_4+_CORNERS'])
        
        # Get top pick (highest probability)
        top_pick = max(picks, key=lambda p: p.get('probability', 0))
        top_match = f"{top_pick['match']['home']} vs {top_pick['match']['away']}"
        top_odds = top_pick['market']['odds']
        top_selection = top_pick['market']['selection']
        
        # Build notification
        title = f"🎯 {len(picks)} Daily Picks Ready!"
        body = f"Top: {top_match}\n{top_selection} @ {top_odds}"
        
        data = {
            "type": "daily_picks",
            "total_picks": len(picks),
            "dc_count": dc_count,
            "btts_count": btts_count,
            "corners_count": corners_count,
            "top_pick_id": top_pick.get('id'),
            "screen": "picks"
        }
        
        return await self.send_bulk_notifications(title, body, data)
