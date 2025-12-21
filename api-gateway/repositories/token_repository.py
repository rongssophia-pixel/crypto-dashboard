"""Token Repository for refresh token tracking"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class TokenRepository:
    """Repository for refresh token operations in PostgreSQL"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """
        Initialize token repository
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
        """
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("TokenRepository initialized")

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=2,
                    max_size=10
                )
                logger.info("Connected to PostgreSQL (tokens)")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL (tokens)")

    async def store_refresh_token(
        self,
        user_id: str,
        token_jti: str,
        expires_at: datetime
    ) -> None:
        """
        Store a refresh token
        
        Args:
            user_id: User ID (UUID string)
            token_jti: Token JTI (unique identifier)
            expires_at: Token expiration timestamp
        """
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO refresh_tokens (user_id, token_jti, expires_at)
            VALUES ($1, $2, $3)
        """

        try:
            # Convert timezone-aware datetime to naive UTC for PostgreSQL TIMESTAMP
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            
            await self.pool.execute(
                query,
                UUID(user_id),
                token_jti,
                expires_at
            )
            logger.debug(f"Stored refresh token {token_jti} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store refresh token: {e}")
            raise

    async def is_token_revoked(self, token_jti: str) -> bool:
        """
        Check if a refresh token is revoked
        
        Args:
            token_jti: Token JTI (unique identifier)
            
        Returns:
            True if token is revoked, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT revoked_at
            FROM refresh_tokens
            WHERE token_jti = $1
        """

        try:
            row = await self.pool.fetchrow(query, token_jti)
            if row:
                return row["revoked_at"] is not None
            # Token not found - consider it revoked for security
            return True
        except Exception as e:
            logger.error(f"Failed to check token revocation status: {e}")
            # On error, consider token revoked for security
            return True

    async def revoke_token(self, token_jti: str) -> bool:
        """
        Revoke a specific refresh token
        
        Args:
            token_jti: Token JTI (unique identifier)
            
        Returns:
            True if revocation successful, False otherwise
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE refresh_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE token_jti = $1 AND revoked_at IS NULL
            RETURNING id
        """

        try:
            row = await self.pool.fetchrow(query, token_jti)
            if row:
                logger.info(f"Revoked refresh token {token_jti}")
                return True
            logger.warning(f"Token {token_jti} not found or already revoked")
            return False
        except Exception as e:
            logger.error(f"Failed to revoke token {token_jti}: {e}")
            raise

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            Number of tokens revoked
        """
        if not self.pool:
            await self.connect()

        query = """
            UPDATE refresh_tokens
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = $1 AND revoked_at IS NULL
        """

        try:
            result = await self.pool.execute(query, UUID(user_id))
            # Parse result like "UPDATE 5" to get count
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Revoked {count} refresh tokens for user {user_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
            raise

    async def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens from database (cleanup job)
        
        Returns:
            Number of tokens deleted
        """
        if not self.pool:
            await self.connect()

        query = """
            DELETE FROM refresh_tokens
            WHERE expires_at < CURRENT_TIMESTAMP
        """

        try:
            result = await self.pool.execute(query)
            count = int(result.split()[-1]) if result else 0
            if count > 0:
                logger.info(f"Cleaned up {count} expired tokens")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            raise
