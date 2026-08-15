"""Repository for console database operations."""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import yaml

from src.models.schemas import (
    ConsoleReference, ConsoleVariant, ConsoleEdition,
    ConsoleListing, ConsoleMatchResult
)
from src.utils.logger import get_logger
from src.utils.listing_versioning import (
    compute_content_fingerprint, ListingVersionManager
)

logger = get_logger("console_repository")


def get_connection():
    """Get database connection using config."""
    config_path = Path(__file__).parent.parent.parent / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    db_config = config['database']
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config.get('port', 5433),
        database=db_config['name'],
        user=db_config['user'],
        password=db_config['password']
    )


class ConsoleRepository:
    """Repository for console data operations."""

    def __init__(self):
        self._consoles: Optional[List[ConsoleReference]] = None
        self._variants: Optional[List[ConsoleVariant]] = None
        self._editions: Optional[List[ConsoleEdition]] = None

    # Reference data loading
    def load_references(self) -> tuple:
        """Load all console reference data."""
        self._consoles = self._load_consoles()
        self._variants = self._load_variants()
        self._editions = self._load_editions()

        logger.info(f"Loaded {len(self._consoles)} consoles, {len(self._variants)} variants, "
                   f"{len(self._editions)} editions")

        return self._consoles, self._variants, self._editions

    def _load_consoles(self) -> List[ConsoleReference]:
        """Load console references from database."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM console_reference ORDER BY name")
                rows = cur.fetchall()
                return [ConsoleReference(**row) for row in rows]

    def _load_variants(self) -> List[ConsoleVariant]:
        """Load console variants from database."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM console_variants ORDER BY model_name")
                rows = cur.fetchall()
                return [ConsoleVariant(**row) for row in rows]

    def _load_editions(self) -> List[ConsoleEdition]:
        """Load console editions from database."""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM console_editions ORDER BY edition_name")
                rows = cur.fetchall()
                return [ConsoleEdition(**row) for row in rows]

    @property
    def consoles(self) -> List[ConsoleReference]:
        """Get cached consoles."""
        if self._consoles is None:
            self.load_references()
        return self._consoles

    @property
    def variants(self) -> List[ConsoleVariant]:
        """Get cached variants."""
        if self._variants is None:
            self.load_references()
        return self._variants

    @property
    def editions(self) -> List[ConsoleEdition]:
        """Get cached editions."""
        if self._editions is None:
            self.load_references()
        return self._editions

    # Listing operations with versioning support
    def save_listing(self, listing: ConsoleListing, match_result: Optional[ConsoleMatchResult] = None) -> Tuple[str, str]:
        """Save or update a console listing with versioning support.

        Returns:
            Tuple of (action, message) where action is 'new', 'updated', 'unchanged', or 'new_version'
        """
        try:
            from sqlalchemy import text
            from src.database.connection import get_session

            with get_session() as session:
                # Compute content fingerprint for versioning
                fingerprint = compute_content_fingerprint(
                    listing.title, listing.description, listing.price_eur, listing.seller_location
                )
                listing.content_hash = fingerprint

                # Check versioning
                version_mgr = ListingVersionManager(session)
                effective_id, version, action_type, _ = version_mgr.check_and_prepare(
                    listing.listing_id, listing.title, listing.description,
                    listing.price_eur, listing.seller_location, "console_listings"
                )

                # Update listing with effective ID and version
                original_id = listing.listing_id
                listing.listing_id = effective_id
                listing.version_number = version

                # Check if this exact version exists
                existing = session.execute(
                    text("SELECT listing_id, content_hash FROM console_listings WHERE listing_id = :id AND version_number = :version"),
                    {"id": effective_id, "version": version}
                ).fetchone()

                if existing:
                    # Check if content changed
                    if existing[1] == fingerprint:
                        # Unchanged, just update last_seen
                        session.execute(
                            text("UPDATE console_listings SET last_seen_at = NOW(), is_active = true WHERE listing_id = :id AND version_number = :version"),
                            {"id": effective_id, "version": version}
                        )
                        return "unchanged", f"Unchanged: {listing.title[:50]}..."

                    # Save version history before updating
                    version_mgr.save_version_history(original_id, version, "console_listings")

                    # Update existing listing
                    self._update_listing_with_session(session, listing, match_result, effective_id, version)
                    return "updated", f"Updated: {listing.title[:50]}..."
                else:
                    # Insert new listing (could be v1 or v2, v3, etc.)
                    self._insert_listing_with_session(session, listing, match_result, effective_id, version)
                    if version > 1:
                        return "new_version", f"New version ({version}): {listing.title[:50]}..."
                    return "new", f"New: {listing.title[:50]}..."

        except Exception as e:
            logger.error(f"Error saving listing {listing.listing_id}: {e}")
            return "failed", f"Error: {str(e)[:50]}"

    def _insert_listing_with_session(self, session, listing: ConsoleListing, match_result: Optional[ConsoleMatchResult], effective_id: str, version: int):
        """Insert new listing with versioning support."""
        from sqlalchemy import text

        if match_result:
            session.execute(text("""
                INSERT INTO console_listings (
                    listing_id, version_number, title, description, price_eur, seller_location,
                    listing_url, image_url, local_image_path, date_posted, matched_console_id,
                    matched_variant_id, matched_edition_id, console_confidence_score,
                    console_match_method, variant_confidence_score, variant_match_method,
                    edition_confidence_score, edition_match_method, is_special_edition,
                    special_edition_note, content_hash, is_active
                ) VALUES (
                    :id, :version, :title, :desc, :price, :location, :url, :img, :local_img, :date,
                    :console_id, :variant_id, :edition_id, :console_conf, :console_method,
                    :variant_conf, :variant_method, :edition_conf, :edition_method,
                    :is_special, :special_note, :hash, true
                )
            """), {
                "id": effective_id,
                "version": version,
                "title": listing.title,
                "desc": listing.description,
                "price": listing.price_eur,
                "location": listing.seller_location,
                "url": listing.listing_url,
                "img": listing.image_url,
                "date": listing.date_posted,
                "console_id": match_result.console.id if match_result.console else None,
                "variant_id": match_result.variant.id if match_result.variant else None,
                "edition_id": match_result.edition.id if match_result.edition else None,
                "console_conf": match_result.console_confidence,
                "console_method": match_result.method,
                "variant_conf": match_result.variant_confidence,
                "variant_method": match_result.method,
                "edition_conf": match_result.edition_confidence,
                "edition_method": match_result.method,
                "is_special": match_result.is_special,
                "special_note": match_result.special_note,
                "hash": listing.content_hash,
                "local_img": listing.local_image_path
            })
        else:
            session.execute(text("""
                INSERT INTO console_listings (
                    listing_id, version_number, title, description, price_eur, seller_location,
                    listing_url, image_url, local_image_path, date_posted, content_hash, is_active
                ) VALUES (
                    :id, :version, :title, :desc, :price, :location, :url, :img, :local_img, :date, :hash, true
                )
            """), {
                "id": effective_id,
                "version": version,
                "title": listing.title,
                "desc": listing.description,
                "price": listing.price_eur,
                "location": listing.seller_location,
                "url": listing.listing_url,
                "img": listing.image_url,
                "date": listing.date_posted,
                "hash": listing.content_hash,
                "local_img": listing.local_image_path
            })

    def _update_listing_with_session(self, session, listing: ConsoleListing, match_result: Optional[ConsoleMatchResult], effective_id: str, version: int):
        """Update existing listing with versioning support."""
        from sqlalchemy import text

        if match_result:
            session.execute(text("""
                UPDATE console_listings SET
                    title = :title, description = :desc, price_eur = :price,
                    seller_location = :location, image_url = :img, local_image_path = :local_img, date_posted = :date,
                    matched_console_id = :console_id, matched_variant_id = :variant_id,
                    matched_edition_id = :edition_id, console_confidence_score = :console_conf,
                    console_match_method = :console_method, variant_confidence_score = :variant_conf,
                    variant_match_method = :variant_method, edition_confidence_score = :edition_conf,
                    edition_match_method = :edition_method, is_special_edition = :is_special,
                    special_edition_note = :special_note, content_hash = :hash,
                    is_active = TRUE, last_seen_at = NOW()
                WHERE listing_id = :id AND version_number = :version
            """), {
                "id": effective_id,
                "version": version,
                "title": listing.title,
                "desc": listing.description,
                "price": listing.price_eur,
                "location": listing.seller_location,
                "img": listing.image_url,
                "date": listing.date_posted,
                "console_id": match_result.console.id if match_result.console else None,
                "variant_id": match_result.variant.id if match_result.variant else None,
                "edition_id": match_result.edition.id if match_result.edition else None,
                "console_conf": match_result.console_confidence,
                "console_method": match_result.method,
                "variant_conf": match_result.variant_confidence,
                "variant_method": match_result.method,
                "edition_conf": match_result.edition_confidence,
                "edition_method": match_result.method,
                "is_special": match_result.is_special,
                "special_note": match_result.special_note,
                "hash": listing.content_hash,
                "local_img": listing.local_image_path
            })
        else:
            session.execute(text("""
                UPDATE console_listings SET
                    title = :title, description = :desc, price_eur = :price,
                    seller_location = :location, image_url = :img, local_image_path = :local_img, date_posted = :date,
                    content_hash = :hash, is_active = TRUE, last_seen_at = NOW()
                WHERE listing_id = :id AND version_number = :version
            """), {
                "id": effective_id,
                "version": version,
                "title": listing.title,
                "desc": listing.description,
                "price": listing.price_eur,
                "location": listing.seller_location,
                "img": listing.image_url,
                "date": listing.date_posted,
                "hash": listing.content_hash,
                "local_img": listing.local_image_path
            })

    # Backward compatibility: old methods that don't use SQLAlchemy session
    def _insert_listing(self, cur, listing: ConsoleListing, match_result: Optional[ConsoleMatchResult]):
        """Insert new listing (legacy method for backward compatibility)."""
        if match_result:
            cur.execute("""
                INSERT INTO console_listings (
                    listing_id, title, description, price_eur, seller_location,
                    listing_url, image_url, date_posted, matched_console_id,
                    matched_variant_id, matched_edition_id, console_confidence_score,
                    console_match_method, variant_confidence_score, variant_match_method,
                    edition_confidence_score, edition_match_method, is_special_edition,
                    special_edition_note, content_hash, previous_listing_id, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                listing.listing_id, listing.title, listing.description, listing.price_eur,
                listing.seller_location, listing.listing_url, listing.image_url,
                listing.date_posted,
                match_result.console.id if match_result.console else None,
                match_result.variant.id if match_result.variant else None,
                match_result.edition.id if match_result.edition else None,
                match_result.console_confidence, match_result.method,
                match_result.variant_confidence, match_result.method,
                match_result.edition_confidence, match_result.method,
                match_result.is_special, match_result.special_note,
                listing.content_hash, listing.previous_listing_id, True
            ))
        else:
            cur.execute("""
                INSERT INTO console_listings (
                    listing_id, title, description, price_eur, seller_location,
                    listing_url, image_url, date_posted, content_hash, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                listing.listing_id, listing.title, listing.description, listing.price_eur,
                listing.seller_location, listing.listing_url, listing.image_url,
                listing.date_posted, listing.content_hash, True
            ))

    def _update_listing(self, cur, listing: ConsoleListing, match_result: Optional[ConsoleMatchResult]):
        """Update existing listing (legacy method for backward compatibility)."""
        # First, get existing match data
        cur.execute("""
            SELECT matched_console_id, console_confidence_score
            FROM console_listings
            WHERE listing_id = %s
        """, (listing.listing_id,))
        existing = cur.fetchone()

        existing_console_id = existing[0] if existing else None
        existing_confidence = existing[1] if existing and len(existing) > 1 else 0.0

        # Decide whether to update match data
        # Keep existing match if:
        # 1. No new match result
        # 2. New match is worse than existing
        # 3. Existing has match but new doesn't
        should_update_match = True
        if existing_console_id and match_result:
            if not match_result.console:
                should_update_match = False  # Keep existing, new has no match
            elif match_result.console_confidence < existing_confidence:
                should_update_match = False  # Keep existing, new is worse

        if should_update_match and match_result:
            cur.execute("""
                UPDATE console_listings SET
                    title = %s, description = %s, price_eur = %s, seller_location = %s,
                    image_url = %s, date_posted = %s, matched_console_id = %s,
                    matched_variant_id = %s, matched_edition_id = %s,
                    console_confidence_score = %s, console_match_method = %s,
                    variant_confidence_score = %s, variant_match_method = %s,
                    edition_confidence_score = %s, edition_match_method = %s,
                    is_special_edition = %s, special_edition_note = %s,
                    content_hash = %s, is_active = TRUE, last_seen_at = NOW()
                WHERE listing_id = %s
            """, (
                listing.title, listing.description, listing.price_eur, listing.seller_location,
                listing.image_url, listing.date_posted,
                match_result.console.id if match_result.console else None,
                match_result.variant.id if match_result.variant else None,
                match_result.edition.id if match_result.edition else None,
                match_result.console_confidence, match_result.method,
                match_result.variant_confidence, match_result.method,
                match_result.edition_confidence, match_result.method,
                match_result.is_special, match_result.special_note,
                listing.content_hash, listing.listing_id
            ))
        else:
            # Update only non-match fields, preserve existing match
            if existing_console_id:
                # Preserve existing match - only update basic fields
                cur.execute("""
                    UPDATE console_listings SET
                        title = %s, description = %s, price_eur = %s, seller_location = %s,
                        image_url = %s, date_posted = %s, content_hash = %s,
                        is_active = TRUE, last_seen_at = NOW()
                    WHERE listing_id = %s
                """, (
                    listing.title, listing.description, listing.price_eur, listing.seller_location,
                    listing.image_url, listing.date_posted, listing.content_hash, listing.listing_id
                ))
            else:
                # No existing match, update normally
                cur.execute("""
                    UPDATE console_listings SET
                        title = %s, description = %s, price_eur = %s, seller_location = %s,
                        image_url = %s, date_posted = %s, content_hash = %s,
                        is_active = TRUE, last_seen_at = NOW()
                    WHERE listing_id = %s
                """, (
                    listing.title, listing.description, listing.price_eur, listing.seller_location,
                    listing.image_url, listing.date_posted, listing.content_hash, listing.listing_id
                ))

    # Scraper log operations
    def log_match(self, scrape_run_id: int, listing_id: str, title: str,
                  match_result: ConsoleMatchResult):
        """Log matching result to console_scraper_log."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO console_scraper_log (
                            scrape_run_id, listing_id, title, matched_console_name,
                            matched_variant_name, matched_edition_name, confidence_console,
                            confidence_variant, confidence_edition, match_method,
                            special_flag, special_note
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        scrape_run_id, listing_id, title,
                        match_result.console.name if match_result.console else None,
                        match_result.variant.model_name if match_result.variant else None,
                        match_result.edition.edition_name if match_result.edition else None,
                        match_result.console_confidence, match_result.variant_confidence,
                        match_result.edition_confidence, match_result.method,
                        match_result.is_special, match_result.special_note
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error logging match: {e}")

    # Scrape run operations
    def start_scrape_run(self) -> int:
        """Start a new scrape run and return its ID."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO console_scrape_runs (status, started_at)
                        VALUES ('running', NOW())
                        RETURNING id
                    """)
                    result = cur.fetchone()
                    conn.commit()
                    return result[0]
        except Exception as e:
            logger.error(f"Error starting scrape run: {e}")
            return None

    def complete_scrape_run(self, run_id: int, stats: Dict[str, int], error: Optional[str] = None):
        """Complete a scrape run."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE console_scrape_runs SET
                            completed_at = NOW(),
                            status = %s,
                            total_listings = %s,
                            new_listings = %s,
                            updated_listings = %s,
                            failed_requests = %s,
                            error_message = %s
                        WHERE id = %s
                    """, (
                        'failed' if error else 'completed',
                        stats.get('total', 0),
                        stats.get('new', 0),
                        stats.get('updated', 0),
                        stats.get('failed', 0),
                        error,
                        run_id
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error completing scrape run: {e}")

    # Query operations
    def get_listings(self, console_id: Optional[int] = None,
                    variant_id: Optional[int] = None,
                    active_only: bool = True,
                    limit: int = 100) -> List[ConsoleListing]:
        """Get listings with optional filters."""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = "SELECT * FROM console_listings WHERE 1=1"
                    params = []

                    if active_only:
                        query += " AND is_active = TRUE"

                    if console_id:
                        query += " AND matched_console_id = %s"
                        params.append(console_id)

                    if variant_id:
                        query += " AND matched_variant_id = %s"
                        params.append(variant_id)

                    query += " ORDER BY date_posted DESC LIMIT %s"
                    params.append(limit)

                    cur.execute(query, params)
                    rows = cur.fetchall()
                    return [ConsoleListing(**row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting listings: {e}")
            return []

    def get_listings_by_console(self, console_name: str) -> List[Dict[str, Any]]:
        """Get listings for a specific console."""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT cl.*,
                               cr.name as console_name,
                               cv.model_name as variant_name,
                               ce.edition_name
                        FROM console_listings cl
                        LEFT JOIN console_reference cr ON cl.matched_console_id = cr.id
                        LEFT JOIN console_variants cv ON cl.matched_variant_id = cv.id
                        LEFT JOIN console_editions ce ON cl.matched_edition_id = ce.id
                        WHERE cr.name ILIKE %s AND cl.is_active = TRUE
                        ORDER BY cl.price_eur ASC
                    """, (f'%{console_name}%',))
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting listings by console: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get console listing statistics."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    stats = {}

                    # Total listings
                    cur.execute("SELECT COUNT(*) FROM console_listings WHERE is_active = TRUE")
                    stats['total_listings'] = cur.fetchone()[0]

                    # By console
                    cur.execute("""
                        SELECT cr.name, COUNT(*) as count
                        FROM console_listings cl
                        JOIN console_reference cr ON cl.matched_console_id = cr.id
                        WHERE cl.is_active = TRUE
                        GROUP BY cr.name
                        ORDER BY count DESC
                    """)
                    stats['by_console'] = cur.fetchall()

                    # Average prices by console
                    cur.execute("""
                        SELECT cr.name, AVG(price_eur) as avg_price
                        FROM console_listings cl
                        JOIN console_reference cr ON cl.matched_console_id = cr.id
                        WHERE cl.is_active = TRUE
                        GROUP BY cr.name
                        ORDER BY avg_price DESC
                    """)
                    stats['avg_prices'] = cur.fetchall()

                    # Special editions
                    cur.execute("""
                        SELECT COUNT(*) FROM console_listings
                        WHERE is_active = TRUE AND is_special_edition = TRUE
                    """)
                    stats['special_editions'] = cur.fetchone()[0]

                    return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
