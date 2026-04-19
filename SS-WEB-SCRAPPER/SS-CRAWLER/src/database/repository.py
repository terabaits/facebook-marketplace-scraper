"""Repository layer for database operations."""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from hashlib import sha256

from sqlalchemy import text, desc
from sqlalchemy.orm import Session

from src.models.schemas import Listing, GPUReference, CPUReference, SSDReference, ScrapeRun, PriceHistory
from src.database.connection import get_session
from src.utils.logger import get_logger

logger = get_logger("repository")


class ListingRepository:
    """CRUD operations for listings."""
    
    @staticmethod
    def get_by_id(session: Session, listing_id: str) -> Optional[Listing]:
        """Get listing by ID."""
        result = session.execute(
            text("SELECT * FROM listings WHERE listing_id = :id"),
            {"id": listing_id}
        ).fetchone()
        
        if result:
            return Listing.model_validate(dict(result._mapping))
        return None
    
    @staticmethod
    def get_by_content_hash(session: Session, content_hash: str) -> Optional[Listing]:
        """Find listing by content hash (duplicate detection)."""
        result = session.execute(
            text("SELECT * FROM listings WHERE content_hash = :hash"),
            {"hash": content_hash}
        ).fetchone()
        
        if result:
            return Listing.model_validate(dict(result._mapping))
        return None
    
    @staticmethod
    def create_or_update(session: Session, listing: Listing, run_id: int) -> Tuple[Listing, str]:
        """
        Create new listing or update existing.
        
        Returns:
            Tuple of (listing, action) where action is 'new', 'updated', 'unchanged', or 'relisted'
        """
        existing = ListingRepository.get_by_id(session, listing.listing_id)
        
        if existing:
            # Check if price changed
            price_changed = existing.price_eur != listing.price_eur
            
            if price_changed:
                # Update with new price
                session.execute(
                    text("""
                        UPDATE listings
                        SET price_eur = :price,
                            description = :desc,
                            is_active = true,
                            last_seen_at = NOW(),
                            updated_at = NOW()
                        WHERE listing_id = :id
                    """),
                    {
                        "id": listing.listing_id,
                        "price": listing.price_eur,
                        "desc": listing.description
                    }
                )
                
                # Add to price history
                session.execute(
                    text("""
                        INSERT INTO price_history (listing_id, price_eur)
                        VALUES (:id, :price)
                    """),
                    {"id": listing.listing_id, "price": listing.price_eur}
                )
                
                logger.info(f"Price updated for {listing.listing_id}: {existing.price_eur} → {listing.price_eur}")
                return listing, "updated"
            
            else:
                # Just update last_seen and match info (in case matching improved)
                # Handle both GPU and CPU listings based on existing category
                if existing.category == 'cpu':
                    session.execute(
                        text("""
                            UPDATE listings
                            SET last_seen_at = NOW(),
                                is_active = true,
                                matched_cpu_id = :cpu_id,
                                cpu_confidence_score = :cpu_confidence,
                                cpu_match_method = :cpu_method
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "cpu_id": listing.matched_cpu_id,
                            "cpu_confidence": listing.cpu_confidence_score,
                            "cpu_method": listing.cpu_match_method
                        }
                    )
                else:
                    session.execute(
                        text("""
                            UPDATE listings
                            SET last_seen_at = NOW(),
                                is_active = true,
                                matched_gpu_id = :gpu_id,
                                confidence_score = :confidence,
                                match_method = :method
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "gpu_id": listing.matched_gpu_id,
                            "confidence": listing.confidence_score,
                            "method": listing.match_method
                        }
                    )
                return listing, "unchanged"
        
        # Check for re-list (same content hash, different ID)
        if listing.content_hash:
            relisted = session.execute(
                text("SELECT listing_id FROM listings WHERE content_hash = :hash"),
                {"hash": listing.content_hash}
            ).fetchone()
            
            if relisted:
                listing.previous_listing_id = relisted[0]
                logger.info(f"Detected re-list: {listing.listing_id} (was {relisted[0]})")
        
        # Create new listing - handle both GPU and CPU
        if listing.category == 'cpu':
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_cpu_id, cpu_confidence_score, cpu_match_method,
                        content_hash, previous_listing_id
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :cpu_id, :cpu_confidence, :cpu_method, :hash, :prev_id
                    )
                """),
                {
                    "id": listing.listing_id,
                    "title": listing.title,
                    "desc": listing.description,
                    "price": listing.price_eur,
                    "location": listing.seller_location,
                    "url": listing.listing_url,
                    "img": listing.image_url,
                    "date": listing.date_posted,
                    "category": listing.category,
                    "cpu_id": listing.matched_cpu_id,
                    "cpu_confidence": listing.cpu_confidence_score,
                    "cpu_method": listing.cpu_match_method,
                    "hash": listing.content_hash,
                    "prev_id": listing.previous_listing_id
                }
            )
        else:
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_gpu_id, confidence_score, match_method,
                        content_hash, previous_listing_id
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :gpu_id, :confidence, :method, :hash, :prev_id
                    )
                """),
                {
                    "id": listing.listing_id,
                    "title": listing.title,
                    "desc": listing.description,
                    "price": listing.price_eur,
                    "location": listing.seller_location,
                    "url": listing.listing_url,
                    "img": listing.image_url,
                    "date": listing.date_posted,
                    "category": listing.category,
                    "gpu_id": listing.matched_gpu_id,
                    "confidence": listing.confidence_score,
                    "method": listing.match_method,
                    "hash": listing.content_hash,
                    "prev_id": listing.previous_listing_id
                }
            )
        
        # Add initial price history
        session.execute(
            text("INSERT INTO price_history (listing_id, price_eur) VALUES (:id, :price)"),
            {"id": listing.listing_id, "price": listing.price_eur}
        )
        
        logger.info(f"New listing created: {listing.listing_id}")
        return listing, "new"
    
    @staticmethod
    def mark_stale(session: Session, days: int = 7) -> int:
        """Mark listings as inactive if not seen for N days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        result = session.execute(
            text("""
                UPDATE listings
                SET is_active = false
                WHERE last_seen_at < :cutoff AND is_active = true
                RETURNING listing_id
            """),
            {"cutoff": cutoff}
        )
        
        stale_ids = [row[0] for row in result.fetchall()]
        if stale_ids:
            logger.info(f"Marked {len(stale_ids)} listings as stale (not seen since {cutoff.date()})")
        
        return len(stale_ids)


class GPUReferenceRepository:
    """Read-only access to GPU reference data."""
    
    @staticmethod
    def get_all(session: Session) -> List[GPUReference]:
        """Get all GPU references."""
        result = session.execute(text("SELECT * FROM gpu_reference"))
        return [GPUReference.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def get_by_id(session: Session, gpu_id: int) -> Optional[GPUReference]:
        """Get GPU by ID."""
        result = session.execute(
            text("SELECT * FROM gpu_reference WHERE id = :id"),
            {"id": gpu_id}
        ).fetchone()
        
        if result:
            return GPUReference.model_validate(dict(result._mapping))
        return None


class CPUReferenceRepository:
    """Read-only access to CPU reference data."""
    
    @staticmethod
    def get_all(session: Session) -> List[CPUReference]:
        """Get all CPU references."""
        result = session.execute(text("SELECT * FROM cpu_reference"))
        return [CPUReference.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def get_by_id(session: Session, cpu_id: int) -> Optional[CPUReference]:
        """Get CPU by ID."""
        result = session.execute(
            text("SELECT * FROM cpu_reference WHERE id = :id"),
            {"id": cpu_id}
        ).fetchone()
        
        if result:
            return CPUReference.model_validate(dict(result._mapping))
        return None


class SSDReferenceRepository:
    """Read-only access to SSD reference data."""
    
    @staticmethod
    def get_all(session: Session) -> List[SSDReference]:
        """Get all SSD references."""
        result = session.execute(text("SELECT * FROM ssd_reference"))
        return [SSDReference.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def get_by_id(session: Session, ssd_id: int) -> Optional[SSDReference]:
        """Get SSD by ID."""
        result = session.execute(
            text("SELECT * FROM ssd_reference WHERE id = :id"),
            {"id": ssd_id}
        ).fetchone()
        
        if result:
            return SSDReference.model_validate(dict(result._mapping))
        return None
    
    @staticmethod
    def get_count(session: Session) -> int:
        """Get total count of SSD references."""
        result = session.execute(text("SELECT COUNT(*) FROM ssd_reference"))
        return result.fetchone()[0]


class ScrapeRunRepository:
    """Track scraping sessions."""
    
    @staticmethod
    def create(session: Session, category: str, config: dict) -> int:
        """Create new scrape run and return ID."""
        result = session.execute(
            text("""
                INSERT INTO scrape_runs (category, config_snapshot)
                VALUES (:category, :config)
                RETURNING id
            """),
            {"category": category, "config": json.dumps(config)}
        )
        return result.fetchone()[0]
    
    @staticmethod
    def complete(session: Session, run_id: int, stats: dict):
        """Mark scrape run as completed with stats."""
        session.execute(
            text("""
                UPDATE scrape_runs
                SET completed_at = NOW(),
                    status = :status,
                    total_listings = :total,
                    new_listings = :new,
                    updated_listings = :updated,
                    skipped_unchanged = :skipped,
                    failed_requests = :failed,
                    error_message = :error
                WHERE id = :run_id
            """),
            {
                "run_id": run_id,
                "status": stats.get("status", "completed"),
                "total": stats.get("total", 0),
                "new": stats.get("new", 0),
                "updated": stats.get("updated", 0),
                "skipped": stats.get("skipped", 0),
                "failed": stats.get("failed", 0),
                "error": stats.get("error")
            }
        )
