"""Repository layer for database operations."""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from hashlib import sha256

from sqlalchemy import text, desc
from sqlalchemy.orm import Session

from src.models.schemas import Listing, GPUReference, CPUReference, SSDReference, RAMReference, ScrapeRun, PriceHistory, GPUBenchmarkReference
from src.database.connection import get_session
from src.utils.logger import get_logger
from src.utils.listing_versioning import (
    ListingVersionManager, compute_content_fingerprint, get_versioned_listing_id
)

logger = get_logger("repository")


class ListingRepository:
    """CRUD operations for listings."""

    @staticmethod
    def save_version(session: Session, listing_id: str) -> bool:
        """
        Save current state to listing_versions before updating.
        Call this BEFORE updating the listing.
        """
        try:
            session.execute(
                text("""
                INSERT INTO listing_versions (
                    listing_id, version_number, title, description,
                    price_eur, seller_location, matched_ssd_id,
                    matched_ram_id, matched_cpu_id, matched_gpu_id,
                    matched_case_id, matched_psu_id,
                    ssd_confidence_score, ram_confidence_score,
                    cpu_confidence_score, confidence_score,
                    case_confidence_score, psu_confidence_score,
                    content_hash
                )
                SELECT
                    listing_id,
                    COALESCE((SELECT MAX(version_number) FROM listing_versions
                              WHERE listing_id = :id), 0) + 1,
                    title, description, price_eur, seller_location,
                    matched_ssd_id, matched_ram_id, matched_cpu_id, matched_gpu_id,
                    matched_case_id, matched_psu_id,
                    ssd_confidence_score, ram_confidence_score,
                    cpu_confidence_score, confidence_score,
                    case_confidence_score, psu_confidence_score,
                    content_hash
                FROM listings
                WHERE listing_id = :id
                """),
                {"id": listing_id}
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to save version for {listing_id}: {e}")
            return False

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
    def update_local_image_path(session: Session, listing_id: str, local_image_path: str) -> bool:
        """Update the local_image_path for a listing."""
        try:
            session.execute(
                text("""
                    UPDATE listings 
                    SET local_image_path = :path,
                        updated_at = NOW()
                    WHERE listing_id = :id
                """),
                {"id": listing_id, "path": local_image_path}
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to update local_image_path for {listing_id}: {e}")
            return False

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
        Create new listing or update existing with versioning support.

        When an ID is reused for different content, creates a new version (e.g., gexxm_v2).

        Returns:
            Tuple of (listing, action) where action is 'new', 'updated', 'unchanged', 'new_version', or 'relisted'
        """
        # Compute content fingerprint for versioning
        fingerprint = compute_content_fingerprint(
            listing.title, listing.description, listing.price_eur, listing.seller_location
        )
        listing.content_hash = fingerprint

        # Check versioning
        version_mgr = ListingVersionManager(session)
        effective_id, version, action_type, _ = version_mgr.check_and_prepare(
            listing.listing_id, listing.title, listing.description,
            listing.price_eur, listing.seller_location, "listings"
        )

        # Check if this listing already exists (by effective_id)
        result = session.execute(
            text("SELECT listing_id, title, price_eur, category, description FROM listings WHERE listing_id = :id"),
            {"id": effective_id}
        )
        existing = result.fetchone()

        if existing:
            # Check if price/title/desc changed using numeric indices
            # existing = (listing_id, title, price_eur, category, description)
            existing_title = existing[1] or ''
            existing_price = existing[2]
            existing_desc = existing[4] or ''
            new_desc = listing.description or ''
            
            price_changed = existing_price != listing.price_eur
            title_changed = existing_title != (listing.title or '')
            desc_changed = existing_desc != new_desc

            # Detect any changes
            has_changes = price_changed or title_changed or desc_changed
            
            logger.debug(f"Change detection for {listing.listing_id}: price={price_changed}, title={title_changed}, desc={desc_changed}")

            if has_changes:
                # Save version history BEFORE updating
                ListingRepository.save_version(session, listing.listing_id)

                # Update with new price
                session.execute(
                    text("""
                        UPDATE listings
                        SET price_eur = :price,
                            title = :title,
                            description = :desc,
                            is_active = true,
                            last_seen_at = NOW(),
                            updated_at = NOW()
                        WHERE listing_id = :id
                    """),
                    {
                        "id": listing.listing_id,
                        "price": listing.price_eur,
                        "title": listing.title,
                        "desc": listing.description
                    }
                )

                # Add to price history
                changes = []
                if price_changed:
                    changes.append(f"price €{existing.price_eur}→€{listing.price_eur}")
                if title_changed:
                    changes.append("title")
                if desc_changed:
                    changes.append("description")

                change_type = ", ".join(changes)

                session.execute(
                    text("""
                        INSERT INTO price_history (listing_id, price_eur, change_type)
                        VALUES (:id, :price, :change_type)
                    """),
                    {"id": listing.listing_id, "price": listing.price_eur, "change_type": change_type}
                )

                logger.info(f"💰 {listing.listing_id}: Updated ({change_type})")
                return listing, "updated"

            else:
                # Just update last_seen and match info (in case matching improved)
                match_info = ""
                if existing.category == 'cpu' and listing.matched_cpu_id:
                    cpu = session.execute(
                        text("SELECT cpu_name FROM cpu_reference WHERE id = :id"),
                        {"id": listing.matched_cpu_id}
                    ).fetchone()
                    if cpu:
                        match_info = f" - {cpu[0]}"

                # Handle various listing types based on existing category
                if existing.category == 'cpu':
                    session.execute(
                        text("""
                            UPDATE listings
                            SET last_seen_at = NOW(),
                                is_active = true,
                                matched_cpu_id = :cpu_id,
                                cpu_confidence_score = :cpu_confidence,
                                cpu_match_method = :cpu_method,
                                description = COALESCE(:desc, description)
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "cpu_id": listing.matched_cpu_id,
                            "cpu_confidence": listing.cpu_confidence_score,
                            "cpu_method": listing.cpu_match_method,
                            "desc": listing.description
                        }
                    )
                elif existing.category == 'lens':
                    session.execute(
                        text("""
                            UPDATE listings
                            SET last_seen_at = NOW(),
                                is_active = true,
                                matched_lens_id = :lens_id,
                                lens_confidence_score = :lens_confidence,
                                lens_match_method = :lens_method,
                                description = COALESCE(:desc, description)
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "lens_id": listing.matched_lens_id,
                            "lens_confidence": listing.lens_confidence_score,
                            "lens_method": listing.lens_match_method,
                            "desc": listing.description
                        }
                    )
                elif existing.category == 'camera':
                    session.execute(
                        text("""
                            UPDATE listings
                            SET last_seen_at = NOW(),
                                is_active = true,
                                matched_camera_id = :camera_id,
                                camera_confidence_score = :camera_confidence,
                                camera_match_method = :camera_method,
                                matched_lens_id = :lens_id,
                                lens_confidence_score = :lens_confidence,
                                lens_match_method = :lens_method,
                                description = COALESCE(:desc, description)
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "camera_id": listing.matched_camera_id,
                            "camera_confidence": listing.camera_confidence_score,
                            "camera_method": listing.camera_match_method,
                            "lens_id": listing.matched_lens_id,
                            "lens_confidence": listing.lens_confidence_score,
                            "lens_method": listing.lens_match_method,
                            "desc": listing.description
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
                                match_method = :method,
                                description = COALESCE(:desc, description)
                            WHERE listing_id = :id
                        """),
                        {
                            "id": listing.listing_id,
                            "gpu_id": listing.matched_gpu_id,
                            "confidence": listing.confidence_score,
                            "method": listing.match_method,
                            "desc": listing.description
                        }
                    )
                
                # Log if description was updated
                if desc_changed and listing.description:
                    logger.info(f"📝 {listing.listing_id}: Description updated")
                
                logger.info(f"⏸️ {listing.listing_id}: Unchanged{match_info}")
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

        # GUARD: Double-check effective_id doesn't exist before INSERT
        check_exists = session.execute(
            text("SELECT 1 FROM listings WHERE listing_id = :id"),
            {"id": effective_id}
        ).fetchone()

        if check_exists:
            logger.warning(f"GUARD: Listing {effective_id} already exists, skipping INSERT")
            return listing, "unchanged"

        # Use effective_id for the new listing
        listing.listing_id = effective_id

        # Create new listing - handle GPU, CPU, Lens, etc.
        # Also track if this is a new version of an existing ID
        action = "new_version" if action_type == "new_version" else "new"

        if listing.category == 'cpu':
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_cpu_id, cpu_confidence_score, cpu_match_method,
                        content_hash, previous_listing_id, source
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :cpu_id, :cpu_confidence, :cpu_method, :hash, :prev_id, :source
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
                    "prev_id": listing.previous_listing_id,
                    "source": listing.source
                }
            )
        elif listing.category == 'lens':
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_lens_id, lens_confidence_score, lens_match_method,
                        content_hash, previous_listing_id, source
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :lens_id, :lens_confidence, :lens_method, :hash, :prev_id, :source
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
                    "lens_id": listing.matched_lens_id,
                    "lens_confidence": listing.lens_confidence_score,
                    "lens_method": listing.lens_match_method,
                    "hash": listing.content_hash,
                    "prev_id": listing.previous_listing_id,
                    "source": listing.source
                }
            )
        elif listing.category == 'camera':
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_camera_id, camera_confidence_score, camera_match_method,
                        matched_lens_id, lens_confidence_score, lens_match_method,
                        content_hash, previous_listing_id, source
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :camera_id, :camera_confidence, :camera_method,
                        :lens_id, :lens_confidence, :lens_method, :hash, :prev_id, :source
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
                    "camera_id": listing.matched_camera_id,
                    "camera_confidence": listing.camera_confidence_score,
                    "camera_method": listing.camera_match_method,
                    "lens_id": listing.matched_lens_id,
                    "lens_confidence": listing.lens_confidence_score,
                    "lens_method": listing.lens_match_method,
                    "hash": listing.content_hash,
                    "prev_id": listing.previous_listing_id,
                    "source": listing.source
                }
            )
        else:
            session.execute(
                text("""
                    INSERT INTO listings (
                        listing_id, title, description, price_eur, seller_location,
                        listing_url, image_url, date_posted, category,
                        matched_gpu_id, confidence_score, match_method,
                        content_hash, previous_listing_id, source
                    ) VALUES (
                        :id, :title, :desc, :price, :location, :url, :img,
                        :date, :category, :gpu_id, :confidence, :method, :hash, :prev_id, :source
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
                    "prev_id": listing.previous_listing_id,
                    "source": listing.source
                }
            )

        # Add initial price history
        session.execute(
            text("INSERT INTO price_history (listing_id, price_eur) VALUES (:id, :price)"),
            {"id": listing.listing_id, "price": listing.price_eur}
        )

        # Log with matched model info
        if listing.category == 'cpu' and listing.matched_cpu_id:
            cpu = session.execute(
                text("SELECT cpu_name FROM cpu_reference WHERE id = :id"),
                {"id": listing.matched_cpu_id}
            ).fetchone()
            if cpu:
                logger.info(f"✨ {listing.listing_id}: New - {cpu[0]}")
            else:
                logger.info(f"✨ {listing.listing_id}: New")
        else:
            logger.info(f"✨ {listing.listing_id}: New")
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

    @staticmethod
    def get_by_source(session: Session, source: str, category: Optional[str] = None, limit: int = 100) -> List[Listing]:
        """Get listings by source marketplace.
        
        Args:
            source: Marketplace source ('ss.com', 'andelemandele', etc.)
            category: Optional category filter
            limit: Max results to return
        """
        if category:
            result = session.execute(
                text("""
                    SELECT * FROM listings 
                    WHERE source = :source AND category = :category
                    ORDER BY date_posted DESC
                    LIMIT :limit
                """),
                {"source": source, "category": category, "limit": limit}
            )
        else:
            result = session.execute(
                text("""
                    SELECT * FROM listings 
                    WHERE source = :source
                    ORDER BY date_posted DESC
                    LIMIT :limit
                """),
                {"source": source, "limit": limit}
            )
        return [Listing.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_all_sources(session: Session) -> List[str]:
        """Get list of all distinct sources in database."""
        result = session.execute(
            text("SELECT DISTINCT source FROM listings WHERE source IS NOT NULL ORDER BY source")
        )
        return [row[0] for row in result.fetchall()]


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


class RAMReferenceRepository:
    """Read-only access to RAM reference data."""

    @staticmethod
    def get_all(session: Session) -> List[RAMReference]:
        """Get all RAM references."""
        result = session.execute(text("SELECT * FROM ram_reference"))
        return [RAMReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, ram_id: int) -> Optional[RAMReference]:
        """Get RAM by ID."""
        result = session.execute(
            text("SELECT * FROM ram_reference WHERE id = :id"),
            {"id": ram_id}
        ).fetchone()

        if result:
            return RAMReference.model_validate(dict(result._mapping))
        return None

    @staticmethod
    def get_count(session: Session) -> int:
        """Get total count of RAM references."""
        result = session.execute(text("SELECT COUNT(*) FROM ram_reference"))
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


class CaseRepository:
    """Read-only access to Case reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Case references."""
        from src.models.schemas import CaseReference
        result = session.execute(text("SELECT * FROM case_reference"))
        return [CaseReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, case_id: int) -> Optional:
        """Get Case by ID."""
        from src.models.schemas import CaseReference
        result = session.execute(
            text("SELECT * FROM case_reference WHERE id = :id"),
            {"id": case_id}
        ).fetchone()

        if result:
            return CaseReference.model_validate(dict(result._mapping))
        return None


class PSURepository:
    """Read-only access to PSU reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all PSU references."""
        from src.models.schemas import PSUReference
        result = session.execute(text("SELECT * FROM psu_reference"))
        return [PSUReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, psu_id: int) -> Optional:
        """Get PSU by ID."""
        from src.models.schemas import PSUReference
        result = session.execute(
            text("SELECT * FROM psu_reference WHERE id = :id"),
            {"id": psu_id}
        ).fetchone()

        if result:
            return PSUReference.model_validate(dict(result._mapping))
        return None


class ConsoleRepository:
    """Read-only access to Console reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Console references."""
        from src.models.schemas import ConsoleReference
        result = session.execute(text("SELECT * FROM console_reference"))
        return [ConsoleReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, console_id: int) -> Optional:
        """Get Console by ID."""
        from src.models.schemas import ConsoleReference
        result = session.execute(
            text("SELECT * FROM console_reference WHERE id = :id"),
            {"id": console_id}
        ).fetchone()

        if result:
            return ConsoleReference.model_validate(dict(result._mapping))
        return None


class ConsoleVariantRepository:
    """Read-only access to Console Variant reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Console Variants."""
        from src.models.schemas import ConsoleVariant
        result = session.execute(text("SELECT * FROM console_variants"))
        return [ConsoleVariant.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, variant_id: int) -> Optional:
        """Get Console Variant by ID."""
        from src.models.schemas import ConsoleVariant
        result = session.execute(
            text("SELECT * FROM console_variants WHERE id = :id"),
            {"id": variant_id}
        ).fetchone()

        if result:
            return ConsoleVariant.model_validate(dict(result._mapping))
        return None

    @staticmethod
    def get_by_console_id(session: Session, console_id: int) -> List:
        """Get all variants for a console."""
        from src.models.schemas import ConsoleVariant
        result = session.execute(
            text("SELECT * FROM console_variants WHERE console_id = :console_id"),
            {"console_id": console_id}
        )
        return [ConsoleVariant.model_validate(dict(row._mapping)) for row in result.fetchall()]


class ConsoleEditionRepository:
    """Read-only access to Console Edition reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Console Editions."""
        from src.models.schemas import ConsoleEdition
        result = session.execute(text("SELECT * FROM console_editions"))
        return [ConsoleEdition.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, edition_id: int) -> Optional:
        """Get Console Edition by ID."""
        from src.models.schemas import ConsoleEdition
        result = session.execute(
            text("SELECT * FROM console_editions WHERE id = :id"),
            {"id": edition_id}
        ).fetchone()

        if result:
            return ConsoleEdition.model_validate(dict(result._mapping))
        return None

    @staticmethod
    def get_by_console_id(session: Session, console_id: int) -> List:
        """Get all editions for a console."""
        from src.models.schemas import ConsoleEdition
        result = session.execute(
            text("SELECT * FROM console_editions WHERE console_id = :console_id"),
            {"console_id": console_id}
        )
        return [ConsoleEdition.model_validate(dict(row._mapping)) for row in result.fetchall()]


class LensReferenceRepository:
    """Read-only access to Lens reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Lens references."""
        result = session.execute(text("SELECT * FROM lens_reference"))
        rows = result.fetchall()
        # Return as dicts since we don't have a LensReference schema model yet
        return [dict(row._mapping) for row in rows]

    @staticmethod
    def get_by_id(session: Session, lens_id: int) -> Optional[dict]:
        """Get Lens by ID."""
        result = session.execute(
            text("SELECT * FROM lens_reference WHERE id = :id"),
            {"id": lens_id}
        ).fetchone()

        if result:
            return dict(result._mapping)
        return None

    @staticmethod
    def get_by_mount(session: Session, mount: str) -> List[dict]:
        """Get all lenses for a specific mount."""
        result = session.execute(
            text("SELECT * FROM lens_reference WHERE mount = :mount"),
            {"mount": mount}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    def get_count(session: Session) -> int:
        """Get total count of Lens references."""
        result = session.execute(text("SELECT COUNT(*) FROM lens_reference"))
        return result.fetchone()[0]


class CameraRepository:
    """Read-only access to Camera reference data."""

    @staticmethod
    def get_all(session: Session) -> List[dict]:
        """Get all Camera references."""
        result = session.execute(text("SELECT * FROM camera_reference"))
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, camera_id: int) -> Optional[dict]:
        """Get Camera by ID."""
        result = session.execute(
            text("SELECT * FROM camera_reference WHERE id = :id"),
            {"id": camera_id}
        ).fetchone()

        if result:
            return dict(result._mapping)
        return None

    @staticmethod
    def get_by_brand(session: Session, brand: str) -> List[dict]:
        """Get all cameras for a specific brand."""
        result = session.execute(
            text("SELECT * FROM camera_reference WHERE brand ILIKE :brand"),
            {"brand": brand}
        )
        return [dict(row._mapping) for row in result.fetchall()]

    @staticmethod
    def get_count(session: Session) -> int:
        """Get total count of Camera references."""
        result = session.execute(text("SELECT COUNT(*) FROM camera_reference"))
        return result.fetchone()[0]


class MotherboardRepository:
    """Read-only access to Motherboard reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Motherboard references."""
        from src.models.schemas import MotherboardReference
        result = session.execute(text("SELECT * FROM motherboard_models"))
        return [MotherboardReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_id(session: Session, mb_id: int) -> Optional:
        """Get Motherboard by ID."""
        from src.models.schemas import MotherboardReference
        result = session.execute(
            text("SELECT * FROM motherboard_models WHERE id = :id"),
            {"id": mb_id}
        ).fetchone()

        if result:
            return MotherboardReference.model_validate(dict(result._mapping))
        return None


class MonitorRepository:
    """Read-only access to Monitor reference data."""

    @staticmethod
    def get_all(session: Session) -> List:
        """Get all Monitor references."""
        from src.models.schemas import MonitorReference
        result = session.execute(text("SELECT * FROM monitor_models"))
        try:
            return [MonitorReference.model_validate(dict(row._mapping)) for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"Could not load monitor references: {e}")
            return []

    @staticmethod
    def get_by_id(session: Session, monitor_id: int) -> Optional:
        """Get Monitor by ID."""
        from src.models.schemas import MonitorReference
        result = session.execute(
            text("SELECT * FROM monitor_models WHERE id = :id"),
            {"id": monitor_id}
        ).fetchone()

        if result:
            return MonitorReference.model_validate(dict(result._mapping))
        return None


class GPUBenchmarkReferenceRepository:
    """Read-write access to PassMark GPU benchmark reference data."""

    @staticmethod
    def upsert(session: Session, record: GPUBenchmarkReference) -> GPUBenchmarkReference:
        """Upsert a PassMark GPU benchmark record linked to gpu_reference."""
        result = session.execute(
            text("""
            INSERT INTO gpu_reference_passmark (
                gpu_reference_id, passmark_id, name, g3d_mark, g2d_mark,
                tdp_w, vram_mb, category, bus_interface, max_memory_mb,
                core_clock_mhz, mem_clock_mhz, rank, samples, price_usd,
                release_date, passmark_href, match_score, match_method, updated_at
            ) VALUES (
                :gpu_reference_id, :passmark_id, :name, :g3d_mark, :g2d_mark,
                :tdp_w, :vram_mb, :category, :bus_interface, :max_memory_mb,
                :core_clock_mhz, :mem_clock_mhz, :rank, :samples, :price_usd,
                :release_date, :passmark_href, :match_score, :match_method, NOW()
            )
            ON CONFLICT (passmark_id) DO UPDATE SET
                gpu_reference_id = EXCLUDED.gpu_reference_id,
                name = EXCLUDED.name,
                g3d_mark = EXCLUDED.g3d_mark,
                g2d_mark = EXCLUDED.g2d_mark,
                tdp_w = EXCLUDED.tdp_w,
                vram_mb = EXCLUDED.vram_mb,
                category = EXCLUDED.category,
                bus_interface = EXCLUDED.bus_interface,
                max_memory_mb = EXCLUDED.max_memory_mb,
                core_clock_mhz = EXCLUDED.core_clock_mhz,
                mem_clock_mhz = EXCLUDED.mem_clock_mhz,
                rank = EXCLUDED.rank,
                samples = EXCLUDED.samples,
                price_usd = EXCLUDED.price_usd,
                release_date = EXCLUDED.release_date,
                passmark_href = EXCLUDED.passmark_href,
                match_score = EXCLUDED.match_score,
                match_method = EXCLUDED.match_method,
                updated_at = NOW()
            RETURNING *
            """),
            record.model_dump(exclude={"id", "created_at"})
        )
        return GPUBenchmarkReference.model_validate(dict(result.fetchone()._mapping))

    @staticmethod
    def get_all(session: Session) -> List[GPUBenchmarkReference]:
        """Get all PassMark GPU benchmark records."""
        from src.models.schemas import GPUBenchmarkReference
        result = session.execute(text("SELECT * FROM gpu_reference_passmark"))
        return [GPUBenchmarkReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_by_gpu_reference_id(session: Session, gpu_reference_id: int) -> List[GPUBenchmarkReference]:
        """Get all PassMark records linked to a gpu_reference id."""
        from src.models.schemas import GPUBenchmarkReference
        result = session.execute(
            text("SELECT * FROM gpu_reference_passmark WHERE gpu_reference_id = :id"),
            {"id": gpu_reference_id}
        )
        return [GPUBenchmarkReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def get_unmatched(session: Session) -> List[GPUBenchmarkReference]:
        """Get PassMark records not linked to any gpu_reference."""
        from src.models.schemas import GPUBenchmarkReference
        result = session.execute(
            text("SELECT * FROM gpu_reference_passmark WHERE gpu_reference_id IS NULL")
        )
        return [GPUBenchmarkReference.model_validate(dict(row._mapping)) for row in result.fetchall()]

    @staticmethod
    def clear_all(session: Session) -> int:
        """Clear all PassMark GPU benchmark records. Returns deleted count."""
        result = session.execute(text("DELETE FROM gpu_reference_passmark"))
        return result.rowcount

