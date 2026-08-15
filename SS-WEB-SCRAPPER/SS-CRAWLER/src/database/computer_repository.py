"""Repository for computer listings database operations."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.connection import get_session
from src.models.computer_schemas import ComputerListing, ComponentBreakdown, FlagData
from src.utils.logger import get_logger

logger = get_logger("computer_repository")


class ComputerRepository:
    """CRUD operations for computer listings."""
    
    @staticmethod
    def get_all(session: Session, active_only: bool = True, limit: int = 1000, offset: int = 0) -> List[ComputerListing]:
        """Get all computer listings."""
        query = "SELECT * FROM computer_listings"
        if active_only:
            query += " WHERE is_active = true"
        query += " ORDER BY last_seen_at DESC LIMIT :limit OFFSET :offset"
        
        result = session.execute(text(query), {"limit": limit, "offset": offset})
        return [ComputerListing.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def get_by_id(session: Session, listing_id: str) -> Optional[ComputerListing]:
        """Get computer listing by ID."""
        result = session.execute(
            text("SELECT * FROM computer_listings WHERE listing_id = :id"),
            {"id": listing_id}
        ).fetchone()
        
        if result:
            return ComputerListing.model_validate(dict(result._mapping))
        return None
    
    @staticmethod
    def get_flagged(session: Session, limit: int = 100) -> List[ComputerListing]:
        """Get all flagged listings."""
        result = session.execute(
            text("SELECT * FROM computer_listings WHERE is_flagged = true ORDER BY flagged_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        return [ComputerListing.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def flag_listing(session: Session, listing_id: str, flag_data: FlagData) -> bool:
        """Flag a listing for review."""
        try:
            session.execute(
                text("""
                    UPDATE computer_listings SET
                        is_flagged = :is_flagged,
                        flag_reason = :reason,
                        flag_comment = :comment,
                        flagged_at = NOW(),
                        flagged_by = :flagged_by
                    WHERE listing_id = :id
                """),
                {
                    "id": listing_id,
                    "is_flagged": flag_data.is_flagged,
                    "reason": flag_data.flag_reason,
                    "comment": flag_data.flag_comment,
                    "flagged_by": flag_data.flagged_by
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to flag listing {listing_id}: {e}")
            return False
    
    @staticmethod
    def get_component_breakdown(session: Session, listing_id: str, 
                                   cpu_repo, gpu_repo, ram_repo, ssd_repo, psu_repo, case_repo) -> Optional[ComponentBreakdown]:
        """Get detailed component breakdown for a listing."""
        listing = ComputerRepository.get_by_id(session, listing_id)
        if not listing:
            return None
        
        breakdown = ComponentBreakdown(
            listing_id=listing.listing_id,
            title=listing.title,
            price_eur=listing.price_eur
        )
        
        # Get CPU details and avg price
        if listing.matched_cpu_id:
            cpu = cpu_repo.get_by_id(session, listing.matched_cpu_id)
            if cpu:
                breakdown.cpu = cpu.model_dump() if hasattr(cpu, 'model_dump') else cpu.__dict__
                # Calculate avg price from similar listings or use reference price
                avg_price = ComputerRepository._get_component_avg_price(
                    session, 'cpu', listing.matched_cpu_id
                )
                breakdown.cpu_avg_price = avg_price or 150.0
        
        # Get GPU details and avg price
        if listing.matched_gpu_id:
            gpu = gpu_repo.get_by_id(session, listing.matched_gpu_id)
            if gpu:
                breakdown.gpu = gpu.model_dump() if hasattr(gpu, 'model_dump') else gpu.__dict__
                avg_price = ComputerRepository._get_component_avg_price(
                    session, 'gpu', listing.matched_gpu_id
                )
                breakdown.gpu_avg_price = avg_price or 250.0
        
        # Get RAM details and avg price
        if listing.matched_ram_id:
            ram = ram_repo.get_by_id(session, listing.matched_ram_id)
            if ram:
                breakdown.ram = ram.model_dump() if hasattr(ram, 'model_dump') else ram.__dict__
                avg_price = ComputerRepository._get_component_avg_price(
                    session, 'ram', listing.matched_ram_id
                )
                breakdown.ram_avg_price = avg_price or 50.0
        
        # Get SSD details and avg price (handles both matched and generic)
        if listing.matched_ssd_id:
            if listing.matched_ssd_id > 0:
                # Matched to reference
                ssd = ssd_repo.get_by_id(session, listing.matched_ssd_id)
                if ssd:
                    breakdown.ssd = ssd.model_dump() if hasattr(ssd, 'model_dump') else ssd.__dict__
                    avg_price = ComputerRepository._get_component_avg_price(
                        session, 'ssd', listing.matched_ssd_id
                    )
                    breakdown.ssd_avg_price = avg_price or 60.0
            else:
                # Generic fallback SSD (ID = -1 or similar)
                # Extract capacity from match_method or use default
                capacity = 256  # Default
                if listing.ssd_match_method and 'GB' in listing.ssd_match_method:
                    import re
                    match = re.search(r'(\d+)GB', listing.ssd_match_method)
                    if match:
                        capacity = int(match.group(1))
                breakdown.ssd = {
                    'name': f'Generic {capacity}GB SSD',
                    'brand': 'Generic',
                    'model': f'{capacity}GB SSD',
                    'capacity_gb': capacity
                }
                # Estimate price based on capacity
                price_map = {128: 25, 240: 35, 256: 40, 480: 50, 500: 55, 512: 60, 1000: 80, 1024: 85, 2000: 150, 2048: 160}
                breakdown.ssd_avg_price = price_map.get(capacity, 60)
        
        # Get SSD2 details (handles both matched and generic)
        if listing.matched_ssd2_id:
            if listing.matched_ssd2_id > 0:
                ssd2 = ssd_repo.get_by_id(session, listing.matched_ssd2_id)
                if ssd2:
                    breakdown.ssd2 = ssd2.model_dump() if hasattr(ssd2, 'model_dump') else ssd2.__dict__
                    avg_price = ComputerRepository._get_component_avg_price(
                        session, 'ssd', listing.matched_ssd2_id
                    )
                    breakdown.ssd2_avg_price = avg_price or 60.0
            else:
                # Generic SSD2
                capacity = 500  # Default
                if listing.ssd2_match_method and 'GB' in listing.ssd2_match_method:
                    import re
                    match = re.search(r'(\d+)GB', listing.ssd2_match_method)
                    if match:
                        capacity = int(match.group(1))
                breakdown.ssd2 = {
                    'name': f'Generic {capacity}GB SSD (2nd)',
                    'brand': 'Generic',
                    'model': f'{capacity}GB SSD',
                    'capacity_gb': capacity
                }
                price_map = {128: 25, 240: 35, 256: 40, 480: 50, 500: 55, 512: 60, 1000: 80, 1024: 85, 2000: 150, 2048: 160}
                breakdown.ssd2_avg_price = price_map.get(capacity, 60)
        
        # Get SSD3 details (handles both matched and generic)
        if listing.matched_ssd3_id:
            if listing.matched_ssd3_id > 0:
                ssd3 = ssd_repo.get_by_id(session, listing.matched_ssd3_id)
                if ssd3:
                    breakdown.ssd3 = ssd3.model_dump() if hasattr(ssd3, 'model_dump') else ssd3.__dict__
                    avg_price = ComputerRepository._get_component_avg_price(
                        session, 'ssd', listing.matched_ssd3_id
                    )
                    breakdown.ssd3_avg_price = avg_price or 60.0
            else:
                # Generic SSD3
                capacity = 256  # Default
                if listing.ssd3_match_method and 'GB' in listing.ssd3_match_method:
                    import re
                    match = re.search(r'(\d+)GB', listing.ssd3_match_method)
                    if match:
                        capacity = int(match.group(1))
                breakdown.ssd3 = {
                    'name': f'Generic {capacity}GB SSD (3rd)',
                    'brand': 'Generic',
                    'model': f'{capacity}GB SSD',
                    'capacity_gb': capacity
                }
                price_map = {128: 25, 240: 35, 256: 40, 480: 50, 500: 55, 512: 60, 1000: 80, 1024: 85, 2000: 150, 2048: 160}
                breakdown.ssd3_avg_price = price_map.get(capacity, 60)
        
        # Get PSU details
        if listing.matched_psu_id:
            psu = psu_repo.get_by_id(session, listing.matched_psu_id)
            if psu:
                breakdown.psu = psu.model_dump() if hasattr(psu, 'model_dump') else psu.__dict__
                breakdown.psu_avg_price = psu.price or 55.0
        else:
            # Fallback PSU
            breakdown.psu = {
                'name': f"Generic {listing.fallback_psu_wattage}W PSU",
                'wattage': listing.fallback_psu_wattage,
                'price': 55.0 if listing.fallback_psu_wattage >= 650 else 35.0
            }
            breakdown.psu_avg_price = breakdown.psu['price']
        
        # Get Case details
        if listing.matched_case_id:
            case = case_repo.get_by_id(session, listing.matched_case_id)
            if case:
                breakdown.case = case.model_dump() if hasattr(case, 'model_dump') else case.__dict__
                breakdown.case_avg_price = case.price or 50.0
        else:
            # Fallback case
            breakdown.case = {'name': 'Generic PC Case', 'price': listing.fallback_case_price}
            breakdown.case_avg_price = listing.fallback_case_price
        
        # Motherboard (always fallback)
        if listing.fallback_motherboard_price:
            breakdown.motherboard = {'name': 'Entry-level Motherboard', 'price': listing.fallback_motherboard_price}
            breakdown.motherboard_price = listing.fallback_motherboard_price
        
        # Calculate totals - include ALL SSDs
        breakdown.detected_total = sum(filter(None, [
            breakdown.cpu_avg_price,
            breakdown.gpu_avg_price,
            breakdown.ram_avg_price,
            breakdown.ssd_avg_price,
            breakdown.ssd2_avg_price,
            breakdown.ssd3_avg_price,
        ])) if any([breakdown.cpu_avg_price, breakdown.gpu_avg_price, 
                    breakdown.ram_avg_price, breakdown.ssd_avg_price,
                    breakdown.ssd2_avg_price, breakdown.ssd3_avg_price]) else None
        
        breakdown.fallback_total = sum(filter(None, [
            breakdown.psu_avg_price,
            breakdown.case_avg_price,
            breakdown.motherboard_price
        ]))
        
        breakdown.grand_total = (breakdown.detected_total or 0) + breakdown.fallback_total
        breakdown.price_difference = listing.price_eur - breakdown.grand_total
        
        return breakdown
    
    @staticmethod
    def _get_component_avg_price(session: Session, component_type: str, component_id: int) -> Optional[float]:
        """Calculate average price for a component from individual listings."""
        # Map component type to table/column
        table_map = {
            'cpu': ('listings', 'matched_cpu_id', 'price_eur'),
            'gpu': ('listings', 'matched_gpu_id', 'price_eur'),
            'ram': ('listings', 'matched_ram_id', 'price_eur'),
            'ssd': ('listings', 'matched_ssd_id', 'price_eur'),
        }
        
        if component_type not in table_map:
            return None
        
        table, id_col, price_col = table_map[component_type]
        
        result = session.execute(
            text(f"""
                SELECT AVG({price_col}) as avg_price
                FROM {table}
                WHERE {id_col} = :component_id AND is_active = true
                AND {price_col} > 0
            """),
            {"component_id": component_id}
        ).fetchone()
        
        if result and result[0]:
            return float(result[0])
        return None
    
    @staticmethod
    def get_stats(session: Session) -> Dict[str, Any]:
        """Get computer listings statistics."""
        total = session.execute(text("SELECT COUNT(*) FROM computer_listings")).scalar()
        active = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE is_active = true")).scalar()
        flagged = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE is_flagged = true")).scalar()
        
        # Component match counts
        with_cpu = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_cpu_id IS NOT NULL")).scalar()
        with_gpu = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_gpu_id IS NOT NULL")).scalar()
        with_ram = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_ram_id IS NOT NULL")).scalar()
        with_ssd = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_ssd_id IS NOT NULL")).scalar()
        with_ssd2 = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_ssd2_id IS NOT NULL")).scalar()
        with_ssd3 = session.execute(text("SELECT COUNT(*) FROM computer_listings WHERE matched_ssd3_id IS NOT NULL")).scalar()
        
        # Price stats
        price_stats = session.execute(text("""
            SELECT 
                AVG(price_eur) as avg_price,
                MIN(price_eur) as min_price,
                MAX(price_eur) as max_price
            FROM computer_listings WHERE is_active = true
        """)).fetchone()
        
        return {
            'total': total,
            'active': active,
            'flagged': flagged,
            'with_cpu': with_cpu,
            'with_gpu': with_gpu,
            'with_ram': with_ram,
            'with_ssd': with_ssd,
            'with_ssd2': with_ssd2,
            'with_ssd3': with_ssd3,
            'avg_price': float(price_stats[0]) if price_stats[0] else 0,
            'min_price': float(price_stats[1]) if price_stats[1] else 0,
            'max_price': float(price_stats[2]) if price_stats[2] else 0,
        }
    
    @staticmethod
    def search(session: Session, query: str, limit: int = 50) -> List[ComputerListing]:
        """Search computer listings by title."""
        result = session.execute(
            text("""
                SELECT * FROM computer_listings
                WHERE title ILIKE :query OR description ILIKE :query
                ORDER BY last_seen_at DESC
                LIMIT :limit
            """),
            {"query": f"%{query}%", "limit": limit}
        )
        return [ComputerListing.model_validate(dict(row._mapping)) for row in result.fetchall()]
    
    @staticmethod
    def get_price_range(session: Session, min_price: float = 0, max_price: float = 10000) -> List[ComputerListing]:
        """Get listings within a price range."""
        result = session.execute(
            text("""
                SELECT * FROM computer_listings
                WHERE price_eur >= :min_price AND price_eur <= :max_price
                AND is_active = true
                ORDER BY price_eur
            """),
            {"min_price": min_price, "max_price": max_price}
        )
        return [ComputerListing.model_validate(dict(row._mapping)) for row in result.fetchall()]