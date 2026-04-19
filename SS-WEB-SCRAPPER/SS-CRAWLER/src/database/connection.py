"""Database connection and session management."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.utils.config import DatabaseConfig
from src.utils.logger import get_logger

logger = get_logger("database")


class DatabaseManager:
    """Manages database connections and sessions."""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls, config: DatabaseConfig = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: DatabaseConfig = None):
        if self._initialized or config is None:
            return
        
        self.config = config
        self._connect()
        self._initialized = True
    
    def _connect(self):
        """Initialize database connection."""
        connection_string = self.config.connection_string
        
        # Create engine with connection pooling
        self._engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before use
            echo=False
        )
        
        # Add event listeners for debugging
        event.listen(self._engine, 'connect', self._on_connect)
        event.listen(self._engine, 'checkout', self._on_checkout)
        
        # Create session factory
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine
        )
        
        logger.info(f"Database connected: {self.config.host}:{self.config.port}/{self.config.name}")
    
    def _on_connect(self, dbapi_conn, connection_record):
        """Called when a new connection is created."""
        logger.debug("New database connection created")
    
    def _on_checkout(self, dbapi_conn, connection_record, connection_proxy):
        """Called when a connection is retrieved from the pool."""
        logger.debug("Database connection checked out from pool")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Usage:
            with db_manager.session() as session:
                # use session
                session.commit()
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call with config first.")
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Get a new session (manual management required)."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized.")
        return self._session_factory()
    
    def close(self):
        """Close all connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# Global instance
_db_manager = None


def init_database(config: DatabaseConfig):
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(config)
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get the initialized database manager."""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Convenience context manager for sessions."""
    manager = get_db_manager()
    with manager.session() as session:
        yield session
