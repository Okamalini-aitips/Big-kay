"""Daily scheduler for 08:30 AM SAST pick generation and notifications"""
import schedule
import time
import asyncio
from datetime import datetime
import pytz
import logging
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from services.pick_generator import PickGenerator
from services.push_notifications import PushNotificationService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# South African timezone
SAST = pytz.timezone('Africa/Johannesburg')

# MongoDB connection for push notifications
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']


def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


async def send_daily_notification(picks):
    """Send push notification with daily picks"""
    try:
        db = get_db()
        push_service = PushNotificationService(db)
        
        result = await push_service.send_daily_picks_notification(picks)
        
        if result.get('success'):
            logger.info(f"📱 Push notification sent to {result.get('sent', 0)} devices")
        else:
            logger.warning(f"⚠️ Push notification failed: {result.get('error')}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Error sending push notification: {e}")
        return {"success": False, "error": str(e)}


def generate_daily_picks():
    """Job that runs daily at 08:30 AM SAST"""
    logger.info("=" * 80)
    logger.info("🎯 DAILY PICK GENERATION STARTED")
    logger.info(f"⏰ Time: {datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S SAST')}")
    logger.info("=" * 80)
    
    try:
        generator = PickGenerator()
        picks = generator.generate_daily_picks(hours_ahead=24)
        
        logger.info(f"✅ Generated {len(picks)} qualified picks")
        
        # Send push notification
        if picks:
            logger.info("📱 Sending push notification...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(send_daily_notification(picks))
            loop.close()
        
        logger.info("=" * 80)
        logger.info("✅ DAILY PICK GENERATION COMPLETE")
        logger.info("=" * 80)
        
        return picks
        
    except Exception as e:
        logger.error(f"❌ Error during pick generation: {e}")
        import traceback
        traceback.print_exc()
        return []


def setup_scheduler():
    """Set up the daily scheduler"""
    # Schedule for 08:30 AM SAST every day (06:30 UTC)
    schedule.every().day.at("06:30").do(generate_daily_picks)
    
    logger.info("📅 Scheduler configured:")
    logger.info("   Daily pick generation + notification: 08:30 AM SAST (06:30 UTC)")
    logger.info("   Waiting for scheduled time...")
    logger.info("")
    
    # Run forever
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    logger.info("🚀 Starting Soccer Betting Bot Scheduler")
    logger.info(f"📍 Timezone: South Africa (SAST)")
    logger.info(f"⏰ Current time: {datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S SAST')}")
    logger.info("")
    
    # Optional: Run once immediately for testing
    # generate_daily_picks()
    
    # Start scheduler
    setup_scheduler()
