"""User Repository for PostgreSQL operations"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user operations in PostgreSQL"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """
        Initialize user repository
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
        """
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("UserRepository initialized")

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=2,
                    max_size=10
                )
                logger.info("Connected to PostgreSQL (users)")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL (users)")

    async def create_user(
        self,
        email: str,
        password_hash: str,
        roles: Optional[List[str]] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            email: User email address
            password_hash: Hashed password
            roles: User roles (default: ['user'])
            is_active: Whether user is active (default: True)
            metadata: Additional user metadata
            
        Returns:
            Created user record as dict
            
        Raises:
            Exception: If user creation fails
        """
        if not self.pool:
            await self.connect()

        if roles is None:
            roles = ["user"]

        query = """
            INSERT INTO users (email, password_hash, roles, is_active, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, roles, is_active, created_at, updated_at, metadata
        """

        try:
            row = await self.pool.fetchrow(
                query,
                email,
                password_hash,
                roles,
                is_active,
                json.dumps(metadata) if metadata else "{}"
            )
            user = dict(row)
            user["id"] = str(user["id"])  # Convert UUID to string
            logger.info(f"Created user {user['id']} with email {email}")
            return user
        except asyncpg.UniqueViolationError:
            logger.warning(f"User with email {email} already exists")
            raise ValueError(f"User with email {email} already exists")
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address
        
        Args:
            email: User email address
            
        Returns:
            User record as dict, or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT id, email, password_hash, roles, is_active, 
                   created_at, updated_at, last_login_at, metadata
            FROM users
            WHERE email = $1
        """

        try:
            row = await self.pool.fetchrow(query, email)
            if row:
                user = dict(row)
                user["id"] = str(user["id"])
                return user
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            User record as dict, or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT id, email, password_hash, roles, is_active,
                   created_at, updated_at, last_login_at, metadata
            FROM users
            WHERE id = $1
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id))
            if row:
                user = dict(row)
                user["id"] = str(user["id"])
                return user
            return None
        except Exception as e:
            logger.error(f"Failed to get user by id {user_id}: {e}")
            raise

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update user's password
        
        Args:
            user_id: User ID (UUID string)
            password_hash: New hashed password
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE users
            SET password_hash = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id), password_hash)
            if row:
                logger.info(f"Updated password for user {user_id}")
                return True
            logger.warning(f"User {user_id} not found for password update")
            return False
        except Exception as e:
            logger.error(f"Failed to update password for user {user_id}: {e}")
            raise

    async def mark_email_verified(self, user_id: str) -> bool:
        """
        Mark user's email as verified by storing verification timestamp in metadata
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE users
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{email_verified_at}',
                to_jsonb(CURRENT_TIMESTAMP::text)
            ),
            updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id))
            if row:
                logger.info(f"Marked email as verified for user {user_id}")
                return True
            logger.warning(f"User {user_id} not found for email verification")
            return False
        except Exception as e:
            logger.error(f"Failed to mark email verified for user {user_id}: {e}")
            raise

    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE users
            SET last_login_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id))
            if row:
                logger.debug(f"Updated last login for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            raise

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            True if deactivation successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE users
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id))
            if row:
                logger.info(f"Deactivated user {user_id}")
                return True
            logger.warning(f"User {user_id} not found for deactivation")
            return False
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            raise

    async def activate_user(self, user_id: str) -> bool:
        """
        Activate a user account
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            True if activation successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE users
            SET is_active = true, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id))
            if row:
                logger.info(f"Activated user {user_id}")
                return True
            logger.warning(f"User {user_id} not found for activation")
            return False
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            raise

    async def is_email_verified(self, user_id: str) -> bool:
        """
        Check if user's email is verified
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            True if email is verified, False otherwise
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        metadata = user.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        return "email_verified_at" in metadata
