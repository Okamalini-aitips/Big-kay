"""Coin Wallet Service for OkaMoney AI Tips

Manages user coin balances, purchases, and spending.
Uses MongoDB for persistent storage.

Coin Packages:
- 100 coins for R50
- 230 coins for R100
- 500 coins for R200

Coin Usage:
- View tips: 1 coin per game
- Build A Bet ticket: 4 coins per ticket
- Mixed Parlay ticket: 4 coins per ticket
- Ticket Machine betslip: 10 coins per betslip

Coins expire 45 days after purchase.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)

# Coin packages
COIN_PACKAGES = {
    'basic': {
        'id': 'basic',
        'coins': 100,
        'price': 50,
        'currency': 'ZAR',
        'label': '100 Coins',
        'description': 'Starter Pack'
    },
    'standard': {
        'id': 'standard',
        'coins': 230,
        'price': 100,
        'currency': 'ZAR',
        'label': '230 Coins',
        'description': 'Most Popular',
        'bonus': 30,
        'featured': True
    },
    'premium': {
        'id': 'premium',
        'coins': 500,
        'price': 200,
        'currency': 'ZAR',
        'label': '500 Coins',
        'description': 'Best Value',
        'bonus': 100
    }
}

# Coin costs
COIN_COSTS = {
    'view_tip': 1,
    'build_a_bet': 4,
    'mixed_parlay': 4,
    'ticket_machine': 10,
}

# Expiry days
COIN_EXPIRY_DAYS = 45


class CoinWalletService:
    """Manages coin wallets for users using MongoDB storage."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.wallets = db.coin_wallets
        self.transactions = db.coin_transactions
    
    async def initialize(self):
        """Create indexes for the collections."""
        await self.wallets.create_index("user_id", unique=True)
        await self.transactions.create_index("user_id")
        await self.transactions.create_index("created_at")
        logger.info("Coin wallet service initialized with indexes")
    
    async def _get_or_create_wallet(self, user_id: str) -> Dict:
        """Get or create a wallet for a user."""
        wallet = await self.wallets.find_one({"user_id": user_id})
        
        if not wallet:
            wallet = {
                "user_id": user_id,
                "balance": 0,
                "total_purchased": 0,
                "total_spent": 0,
                "expires_at": None,
                "is_subscribed": False,
                "subscription_expires": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await self.wallets.insert_one(wallet)
        
        # Check and handle expired coins
        if wallet.get("expires_at") and wallet["expires_at"] < datetime.utcnow():
            wallet["balance"] = 0
            wallet["expires_at"] = None
            await self.wallets.update_one(
                {"user_id": user_id},
                {"$set": {"balance": 0, "expires_at": None, "updated_at": datetime.utcnow()}}
            )
        
        return wallet
    
    async def get_balance(self, user_id: str) -> Dict:
        """Get user's coin balance and wallet info."""
        wallet = await self._get_or_create_wallet(user_id)
        
        # Get daily free usage for today
        today = datetime.utcnow().strftime('%Y-%m-%d')
        daily_free = wallet.get('daily_free_used', {})
        
        return {
            'balance': wallet['balance'],
            'expires_at': wallet.get('expires_at').isoformat() if wallet.get('expires_at') else None,
            'is_subscribed': wallet.get('is_subscribed', False),
            'subscription_expires': wallet.get('subscription_expires'),
            'daily_free_betslip_used': daily_free.get(f'ticket_machine_{today}', False),
            'daily_free_build_bet_used': daily_free.get(f'build_a_bet_{today}', False),
            'daily_free_mixed_parlay_used': daily_free.get(f'mixed_parlay_{today}', False),
            'total_purchased': wallet.get('total_purchased', 0),
            'total_spent': wallet.get('total_spent', 0)
        }
    
    async def purchase_coins(self, user_id: str, package_id: str) -> Dict:
        """
        Purchase a coin package.
        Any purchase resets the 45-day expiry for the ENTIRE wallet.
        """
        if package_id not in COIN_PACKAGES:
            return {'success': False, 'error': 'Invalid package'}
        
        package = COIN_PACKAGES[package_id]
        wallet = await self._get_or_create_wallet(user_id)
        
        # New expiry date for ALL coins (45 days from now)
        new_expiry = datetime.utcnow() + timedelta(days=COIN_EXPIRY_DAYS)
        
        # Calculate new balance
        current_balance = wallet['balance']
        new_coins = package['coins']
        total_balance = current_balance + new_coins
        
        # Update wallet
        await self.wallets.update_one(
            {"user_id": user_id},
            {"$set": {
                "balance": total_balance,
                "expires_at": new_expiry,
                "total_purchased": wallet.get('total_purchased', 0) + new_coins,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Record transaction
        await self.transactions.insert_one({
            "user_id": user_id,
            "type": "purchase",
            "amount": new_coins,
            "package_id": package_id,
            "price": package['price'],
            "currency": "ZAR",
            "previous_balance": current_balance,
            "new_balance": total_balance,
            "expires_at": new_expiry,
            "created_at": datetime.utcnow()
        })
        
        return {
            'success': True,
            'new_balance': total_balance,
            'coins_added': new_coins,
            'expires_at': new_expiry.isoformat(),
            'message': f"Added {new_coins} coins! All {total_balance} coins expire in 45 days."
        }
    
    async def spend_coins(self, user_id: str, amount: int, spend_type: str, item_id: str = None) -> Dict:
        """Spend coins on viewing tips or generating betslips."""
        wallet = await self._get_or_create_wallet(user_id)
        
        if wallet['balance'] < amount:
            return {
                'success': False,
                'error': 'Insufficient coins',
                'balance': wallet['balance'],
                'required': amount
            }
        
        new_balance = wallet['balance'] - amount
        
        # Update wallet
        await self.wallets.update_one(
            {"user_id": user_id},
            {"$set": {
                "balance": new_balance,
                "total_spent": wallet.get('total_spent', 0) + amount,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Record transaction
        await self.transactions.insert_one({
            "user_id": user_id,
            "type": "spend",
            "spend_type": spend_type,
            "amount": -amount,
            "item_id": item_id,
            "previous_balance": wallet['balance'],
            "new_balance": new_balance,
            "created_at": datetime.utcnow()
        })
        
        return {
            'success': True,
            'new_balance': new_balance,
            'spent': amount,
            'spend_type': spend_type
        }
    
    async def use_daily_free(self, user_id: str, feature: str) -> Dict:
        """Use daily free access for a feature (subscribed users only)."""
        wallet = await self._get_or_create_wallet(user_id)
        
        if not wallet.get('is_subscribed', False):
            return {'success': False, 'error': 'Subscription required for free access'}
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        key = f'{feature}_{today}'
        
        daily_free = wallet.get('daily_free_used', {})
        
        if daily_free.get(key, False):
            return {'success': False, 'error': 'Daily free already used', 'already_used': True}
        
        daily_free[key] = True
        
        await self.wallets.update_one(
            {"user_id": user_id},
            {"$set": {"daily_free_used": daily_free, "updated_at": datetime.utcnow()}}
        )
        
        return {'success': True, 'feature': feature}
    
    async def check_daily_free(self, user_id: str, feature: str) -> bool:
        """Check if daily free is still available for a feature."""
        wallet = await self._get_or_create_wallet(user_id)
        
        if not wallet.get('is_subscribed', False):
            return False
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        key = f'{feature}_{today}'
        
        return not wallet.get('daily_free_used', {}).get(key, False)
    
    async def set_subscription(self, user_id: str, is_subscribed: bool, expires: str = None) -> Dict:
        """Set user subscription status."""
        await self.wallets.update_one(
            {"user_id": user_id},
            {"$set": {
                "is_subscribed": is_subscribed,
                "subscription_expires": expires,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        return {'success': True, 'is_subscribed': is_subscribed, 'expires': expires}
    
    async def get_transaction_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent transaction history."""
        cursor = self.transactions.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit)
        
        transactions = []
        async for tx in cursor:
            tx['id'] = str(tx.pop('_id'))
            if 'created_at' in tx:
                tx['created_at'] = tx['created_at'].isoformat()
            if 'expires_at' in tx and tx['expires_at']:
                tx['expires_at'] = tx['expires_at'].isoformat()
            transactions.append(tx)
        
        return transactions
    
    async def add_bonus_coins(self, user_id: str, amount: int, reason: str) -> Dict:
        """Add bonus coins (for promotions, etc.)."""
        wallet = await self._get_or_create_wallet(user_id)
        
        new_expiry = datetime.utcnow() + timedelta(days=COIN_EXPIRY_DAYS)
        total_balance = wallet['balance'] + amount
        
        await self.wallets.update_one(
            {"user_id": user_id},
            {"$set": {
                "balance": total_balance,
                "expires_at": new_expiry,
                "updated_at": datetime.utcnow()
            }}
        )
        
        await self.transactions.insert_one({
            "user_id": user_id,
            "type": "bonus",
            "amount": amount,
            "reason": reason,
            "previous_balance": wallet['balance'],
            "new_balance": total_balance,
            "expires_at": new_expiry,
            "created_at": datetime.utcnow()
        })
        
        return {
            'success': True,
            'new_balance': total_balance,
            'bonus_added': amount,
            'expires_at': new_expiry.isoformat()
        }


# Singleton
_coin_wallet_service = None


def get_coin_wallet_service(db: AsyncIOMotorDatabase = None) -> CoinWalletService:
    """Get or create the coin wallet service singleton."""
    global _coin_wallet_service
    if _coin_wallet_service is None and db is not None:
        _coin_wallet_service = CoinWalletService(db)
    return _coin_wallet_service


def get_coin_packages():
    """Get available coin packages."""
    return COIN_PACKAGES


def get_coin_costs():
    """Get coin costs for various actions."""
    return COIN_COSTS
