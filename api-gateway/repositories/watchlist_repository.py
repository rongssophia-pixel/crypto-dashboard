"""Watchlist Repository for PostgreSQL operations"""

import asyncio
import logging
from typing import List, Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class WatchlistRepository:
    """Repository for watchlist operations in PostgreSQL"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        """
        Initialize watchlist repository
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
        """
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.pool: Optional[asyncpg.Pool] = None
        logger.info("WatchlistRepository initialized")

    async def ensure_schema(self):
        """Ensure database schema exists"""
        if not self.pool:
            return

        query = """
            CREATE TABLE IF NOT EXISTS user_watchlists (
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, symbol)
            );
            
            CREATE INDEX IF NOT EXISTS idx_user_watchlists_user_id ON user_watchlists(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_watchlists_symbol ON user_watchlists(symbol);
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query)
                logger.info("✅ Watchlist schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize watchlist schema: {e}")
            raise

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            try:
                logger.info(f"Attempting to create PostgreSQL connection pool (watchlist)...")
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=2,
                    max_size=10,
                    timeout=10,
                    command_timeout=10
                )
                await self.ensure_schema()
                logger.info("✅ Connected to PostgreSQL (watchlist)")
            except asyncio.TimeoutError:
                logger.error("❌ Connection timeout to PostgreSQL (watchlist) after 10 seconds")
                raise
            except Exception as e:
                logger.error(f"❌ Failed to connect to PostgreSQL (watchlist): {type(e).__name__}: {e}")
                raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL (watchlist)")

    async def add_to_watchlist(self, user_id: str, symbol: str) -> bool:
        """
        Add a symbol to user's watchlist
        
        Args:
            user_id: User ID (UUID string)
            symbol: Crypto symbol (e.g., BTCUSDT)
            
        Returns:
            True if added, False if already exists
        """
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO user_watchlists (user_id, symbol)
            VALUES ($1, $2)
            ON CONFLICT (user_id, symbol) DO NOTHING
            RETURNING symbol
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id), symbol)
            if row:
                logger.info(f"Added {symbol} to watchlist for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add to watchlist: {e}")
            raise

    async def remove_from_watchlist(self, user_id: str, symbol: str) -> bool:
        """
        Remove a symbol from user's watchlist
        
        Args:
            user_id: User ID (UUID string)
            symbol: Crypto symbol
            
        Returns:
            True if removed, False if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            DELETE FROM user_watchlists
            WHERE user_id = $1 AND symbol = $2
            RETURNING symbol
        """

        try:
            row = await self.pool.fetchrow(query, UUID(user_id), symbol)
            if row:
                logger.info(f"Removed {symbol} from watchlist for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove from watchlist: {e}")
            raise

    async def get_watchlist(self, user_id: str) -> List[str]:
        """
        Get user's watchlist
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            List of symbols
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT symbol
            FROM user_watchlists
            WHERE user_id = $1
            ORDER BY created_at DESC
        """

        try:
            rows = await self.pool.fetch(query, UUID(user_id))
            return [row["symbol"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            raise

