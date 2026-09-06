"""Authentication Service for OkaMoney AI Tips

Handles user registration, login, and JWT token management.
Uses MongoDB for persistent user storage.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import bcrypt
import jwt
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET') or 'okamoney-jwt-secret-key-change-in-production'
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 days


class AuthService:
    """Handles user authentication with MongoDB storage."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users = db.users
    
    async def initialize(self):
        """Create indexes for the users collection."""
        await self.users.create_index("email", unique=True)
        logger.info("Auth service initialized with user indexes")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError("Password must be at most 72 bytes")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    def _create_token(self, user_id: str) -> str:
        """Create a JWT token for a user."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRE_HOURS)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify a JWT token and return the user_id if valid."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id and ObjectId.is_valid(user_id):
                return user_id
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def register(self, email: str, password: str, name: str = "") -> Dict:
        """Register a new user."""
        email = email.strip().lower()
        
        # Validate password length
        if len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters"}
        
        if len(password.encode('utf-8')) > 72:
            return {"success": False, "error": "Password too long"}
        
        # Check if user exists
        existing = await self.users.find_one({"email": email})
        if existing:
            return {"success": False, "error": "Email already registered"}
        
        # Create user document
        user_doc = {
            "email": email,
            "password_hash": self._hash_password(password),
            "name": name.strip() if name else email.split('@')[0],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "is_admin": False
        }
        
        try:
            result = await self.users.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            # Create token
            token = self._create_token(user_id)
            
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": user_doc["name"]
                },
                "token": token
            }
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {"success": False, "error": "Registration failed"}
    
    async def login(self, email: str, password: str) -> Dict:
        """Authenticate a user and return a token."""
        email = email.strip().lower()
        
        # Find user
        user = await self.users.find_one({"email": email})
        
        # Always run password check to prevent timing attacks
        dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=12)).decode()
        password_valid = self._verify_password(
            password,
            user["password_hash"] if user else dummy_hash
        )
        
        if not user or not password_valid:
            return {"success": False, "error": "Invalid email or password"}
        
        if not user.get("is_active", True):
            return {"success": False, "error": "Account is disabled"}
        
        # Update last login
        await self.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create token
        user_id = str(user["_id"])
        token = self._create_token(user_id)
        
        return {
            "success": True,
            "user": {
                "id": user_id,
                "email": user["email"],
                "name": user.get("name", ""),
                "is_admin": user.get("is_admin", False)
            },
            "token": token
        }
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        if not ObjectId.is_valid(user_id):
            return None
        
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "is_admin": user.get("is_admin", False),
            "created_at": user.get("created_at", "").isoformat() if user.get("created_at") else None
        }
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        user = await self.users.find_one({"email": email.strip().lower()})
        if not user:
            return None
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "is_admin": user.get("is_admin", False)
        }
    
    async def update_user(self, user_id: str, updates: Dict) -> Dict:
        """Update user profile."""
        if not ObjectId.is_valid(user_id):
            return {"success": False, "error": "Invalid user ID"}
        
        allowed_fields = {"name"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return {"success": False, "error": "No valid fields to update"}
        
        filtered_updates["updated_at"] = datetime.utcnow()
        
        result = await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": filtered_updates}
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "User not found"}
        
        return {"success": True}
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict:
        """Change user password."""
        if not ObjectId.is_valid(user_id):
            return {"success": False, "error": "Invalid user ID"}
        
        if len(new_password) < 8:
            return {"success": False, "error": "New password must be at least 8 characters"}
        
        user = await self.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {"success": False, "error": "User not found"}
        
        if not self._verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "Current password is incorrect"}
        
        new_hash = self._hash_password(new_password)
        await self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
        )
        
        return {"success": True}


# Singleton
_auth_service = None


def get_auth_service(db: AsyncIOMotorDatabase) -> AuthService:
    """Get or create the auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(db)
    return _auth_service
