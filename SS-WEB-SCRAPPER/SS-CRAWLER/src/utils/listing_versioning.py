"""Listing versioning utilities for handling reused listing IDs.

When ss.com reuses an ID for a completely different listing (e.g., gexxm now
points to a different item), we detect this and create a new version:
- Original: gexxm (version 1)
- After ID reuse with different content: gexxm_v2 (version 2)
- And so on: gexxm_v3, gexxm_v4, etc.
"""

import hashlib
from typing import Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.utils.logger import get_logger

logger = get_logger("listing_versioning")


@dataclass
class VersionCheckResult:
    """Result of checking if a listing needs versioning."""
    listing_id: str
    version: int
    is_new_version: bool
    previous_version: Optional[int] = None
    action: str = ""  # 'new', 'update', 'new_version'


def compute_content_fingerprint(
    title: str,
    description: Optional[str],
    price: float,
    location: Optional[str] = None
) -> str:
    """
    Compute a fingerprint of the listing content for comparison.
    Used to detect when an ID points to different content.
    
    Args:
        title: Listing title
        description: Listing description
        price: Listing price
        location: Seller location
        
    Returns:
        SHA256 hash of normalized content
    """
    # Normalize inputs
    norm_title = (title or "").lower().strip()
    norm_desc = (description or "").lower().strip()[:500]  # First 500 chars
    norm_loc = (location or "").lower().strip()
    
    # Create consistent string
    content = f"{norm_title}|{norm_desc}|{price:.2f}|{norm_loc}"
    
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def check_listing_version(
    session: Session,
    listing_id: str,
    content_fingerprint: str,
    table_name: str = "listings"
) -> VersionCheckResult:
    """
    Check if a listing ID needs versioning based on content fingerprint.
    
    Args:
        session: Database session
        listing_id: The ss.com listing ID (e.g., 'gexxm')
        content_fingerprint: Computed fingerprint of current content
        table_name: 'listings' or 'computer_listings'
        
    Returns:
        VersionCheckResult with version number and action
    """
    # Query all matching listings and find the one with highest version
    if table_name == "listings":
        query = text("""
            SELECT listing_id, version_number, content_fingerprint, title, price_eur
            FROM listings
            WHERE listing_id = :listing_id OR listing_id LIKE :listing_id_pattern
        """)
    else:
        query = text("""
            SELECT listing_id, version_number, content_fingerprint, title, price_eur
            FROM computer_listings
            WHERE listing_id = :listing_id OR listing_id LIKE :listing_id_pattern
        """)
    
    rows = session.execute(query, {
        "listing_id": listing_id,
        "listing_id_pattern": f"{listing_id}_v%"
    }).fetchall()
    
    # Find the row with highest version number (extracted from listing_id)
    def extract_version(row):
        lid = row[0]
        if "_v" in lid:
            try:
                return int(lid.split("_v")[-1])
            except ValueError:
                pass
        return 1
    
    if not rows:
        result = None
    else:
        # Sort by extracted version descending and take the first
        rows_sorted = sorted(rows, key=lambda r: extract_version(r), reverse=True)
        result = rows_sorted[0]
    
    if listing_id == "gfokc":
        logger.warning(f"DEBUG: Found {len(rows)} rows, picked {result[0] if result else None}")
        for r in rows:
            logger.warning(f"  {r[0]}: hash={r[2][:15] if r[2] else 'NULL'}...")
    
    if not result:
        # No existing listing with this ID - it's new
        return VersionCheckResult(
            listing_id=listing_id,
            version=1,
            is_new_version=False,
            action="new"
        )
    
    # Use the extracted version from the listing_id (e.g., gfokc_v2 -> 2)
    actual_version = extract_version(result)  # Extract from listing_id
    existing_fingerprint = result[2]
    existing_title = result[3]
    
    # Debug
    if listing_id == "gfokc":
        logger.warning(f"DEBUG: using actual_version={actual_version}")
    
    # Handle legacy rows where content_fingerprint might be NULL
    if existing_fingerprint is None:
        # For legacy data, compute fingerprint from actual content and compare
        # Query the actual content of the SPECIFIC version we found
        actual_listing_id = result[0]  # Could be 'bkhnbj' or 'bkhnbj_v2'
        legacy_query = text("""
            SELECT title, description, price_eur, seller_location
            FROM listings
            WHERE listing_id = :listing_id
            ORDER BY version_number DESC
            LIMIT 1
        """)
        legacy_row = session.execute(legacy_query, {"listing_id": actual_listing_id}).fetchone()
        
        if legacy_row:
            # Compute fingerprint from existing DB content
            legacy_fingerprint = compute_content_fingerprint(
                legacy_row[0],  # title
                legacy_row[1],  # description
                legacy_row[2],  # price_eur
                legacy_row[3]   # seller_location
            )
            
            # Compare computed fingerprints
            if legacy_fingerprint == content_fingerprint:
                # Same content - update existing version
                logger.info(f"Legacy listing {listing_id} v{actual_version} matches by computed fingerprint, updating")
                return VersionCheckResult(
                    listing_id=listing_id,
                    version=actual_version,
                    is_new_version=False,
                    previous_version=actual_version,
                    action="update"
                )
        
        # Different content or couldn't compare - create new version
        logger.warning(f"Legacy listing {listing_id} v{actual_version} has NULL fingerprint, creating new version")
        new_version = actual_version + 1
        return VersionCheckResult(
            listing_id=listing_id,
            version=new_version,
            is_new_version=True,
            previous_version=actual_version,
            action="new_version"
        )
    
    # Compare fingerprints
    if existing_fingerprint == content_fingerprint:
        # Same content - this is an update to existing version
        return VersionCheckResult(
            listing_id=listing_id,
            version=actual_version,
            is_new_version=False,
            previous_version=actual_version,
            action="update"
        )
    
    # Different content - need new version
    new_version = actual_version + 1
    logger.info(
        f"Detected ID reuse for {listing_id}: "
        f"'{existing_title}' (v{actual_version}) → new listing (v{new_version})"
    )
    
    return VersionCheckResult(
        listing_id=listing_id,
        version=new_version,
        is_new_version=True,
        previous_version=actual_version,
        action="new_version"
    )


def get_versioned_listing_id(listing_id: str, version: int) -> str:
    """
    Generate the versioned listing ID string.
    
    Args:
        listing_id: Base listing ID (e.g., 'gexxm')
        version: Version number
        
    Returns:
        Versioned ID (e.g., 'gexxm' for v1, 'gexxm_v2' for v2)
    """
    if version <= 1:
        return listing_id
    return f"{listing_id}_v{version}"


def parse_versioned_id(versioned_id: str) -> Tuple[str, int]:
    """
    Parse a versioned ID into base ID and version number.
    
    Args:
        versioned_id: Versioned ID string (e.g., 'gexxm_v2')
        
    Returns:
        Tuple of (base_id, version)
    """
    if "_v" in versioned_id:
        parts = versioned_id.rsplit("_v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
    return versioned_id, 1


class ListingVersionManager:
    """Manager class for handling listing versions across all scrapers."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_and_prepare(
        self,
        listing_id: str,
        title: str,
        description: Optional[str],
        price: float,
        location: Optional[str] = None,
        table_name: str = "listings"
    ) -> Tuple[str, int, str]:
        """
        Check if listing needs versioning and prepare for insertion.
        
        Args:
            listing_id: The ss.com listing ID
            title: Listing title
            description: Listing description
            price: Listing price
            location: Seller location
            table_name: 'listings' or 'computer_listings'
            
        Returns:
            Tuple of (effective_id, version, action)
            - effective_id: ID to use for database operations
            - version: version number
            - action: 'new', 'update', or 'new_version'
        """
        fingerprint = compute_content_fingerprint(title, description, price, location)
        result = check_listing_version(self.session, listing_id, fingerprint, table_name)
        
        effective_id = get_versioned_listing_id(listing_id, result.version)
        
        return effective_id, result.version, result.action, fingerprint
    
    def save_version_history(
        self,
        listing_id: str,
        version: int,
        table_name: str = "listings"
    ) -> bool:
        """
        Save current listing state to version history before updating.
        
        Args:
            listing_id: Base listing ID
            version: Current version to save
            table_name: 'listings' or 'computer_listings'
            
        Returns:
            True if saved successfully
        """
        try:
            if table_name == "listings":
                self.session.execute(
                    text("""
                        INSERT INTO listing_versions (
                            listing_id, version_number, title, description,
                            price_eur, seller_location, matched_gpu_id, matched_cpu_id,
                            confidence_score, cpu_confidence_score, content_hash,
                            created_at
                        )
                        SELECT 
                            listing_id, :version, title, description,
                            price_eur, seller_location, matched_gpu_id, matched_cpu_id,
                            confidence_score, cpu_confidence_score, content_hash,
                            NOW()
                        FROM listings
                        WHERE listing_id = :id AND version_number = :version
                    """),
                    {"id": listing_id, "version": version}
                )
            else:
                self.session.execute(
                    text("""
                        INSERT INTO computer_listing_versions (
                            listing_id, version_number, title, description,
                            price_eur, seller_location, matched_cpu_id, matched_gpu_id,
                            matched_ram_id, matched_ssd_id, matched_psu_id, matched_case_id,
                            cpu_confidence, gpu_confidence, ram_confidence,
                            ssd_confidence, psu_confidence, case_confidence,
                            content_hash, created_at
                        )
                        SELECT 
                            listing_id, :version, title, description,
                            price_eur, seller_location, matched_cpu_id, matched_gpu_id,
                            matched_ram_id, matched_ssd_id, matched_psu_id, matched_case_id,
                            cpu_confidence, gpu_confidence, ram_confidence,
                            ssd_confidence, psu_confidence, case_confidence,
                            content_hash, NOW()
                        FROM computer_listings
                        WHERE listing_id = :id AND version_number = :version
                    """),
                    {"id": listing_id, "version": version}
                )
            return True
        except Exception as e:
            logger.warning(f"Failed to save version history for {listing_id}: {e}")
            return False
