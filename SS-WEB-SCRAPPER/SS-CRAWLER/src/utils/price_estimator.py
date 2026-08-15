"""Price estimator: derives current market prices for computer components from listings table."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from typing import Optional
from src.database.connection import get_session
from sqlalchemy import text


class PriceEstimator:
    """Estimate component prices using actual marketplace listing data."""

    def __init__(self):
        pass

    def _avg(self, category: str, match_col: str, match_id) -> Optional[float]:
        if not match_id:
            return None
        with get_session() as session:
            result = session.execute(
                text(f"""
                    SELECT ROUND(AVG(price_eur)::numeric, 2) as avg_price, COUNT(*) as cnt
                    FROM listings
                    WHERE category = :cat AND {match_col} = :mid
                """),
                {"cat": category, "mid": match_id}
            ).fetchone()
            if result and result[0] and result[1] > 0:
                return float(result[0])
        return None

    def get_cpu_price(self, cpu_id: int) -> Optional[float]:
        return self._avg('cpu', 'matched_cpu_id', cpu_id)

    def get_gpu_price(self, gpu_id: int) -> Optional[float]:
        return self._avg('gpu', 'matched_gpu_id', gpu_id)

    def get_ram_price(self, ram_id: int) -> Optional[float]:
        return self._avg('ram', 'matched_ram_id', ram_id)

    def get_ssd_price(self, ssd_id: int) -> Optional[float]:
        return self._avg('ssd', 'matched_ssd_id', ssd_id)

    def get_generic_ram_price(self, capacity_gb: int, ddr_type: str = 'DDR4') -> float:
        if not capacity_gb:
            return 50.0
        with get_session() as session:
            result = session.execute(
                text("""
                    SELECT ROUND(AVG(l.price_eur)::numeric, 2) as avg_price, COUNT(*) as cnt
                    FROM listings l
                    JOIN ram_reference r ON l.matched_ram_id = r.id
                    WHERE l.category = 'ram'
                      AND l.is_active = true
                      AND r.capacity_gb = :cap
                """),
                {"cap": capacity_gb}
            ).fetchone()
            if result and result[0] and result[1] >= 3:
                return float(result[0])
        fallbacks = {4: 25.0, 8: 35.0, 16: 65.0, 32: 120.0, 64: 250.0}
        return fallbacks.get(capacity_gb, 50.0)

    def get_generic_ssd_price(self, capacity_gb: int) -> float:
        if not capacity_gb:
            return 72.0
        with get_session() as session:
            if 480 <= capacity_gb <= 512:
                title_filter = '%500GB%' if capacity_gb >= 500 else '%480GB%'
            elif 1900 <= capacity_gb <= 2048:
                title_filter = '%2000GB%'
            else:
                title_filter = f'%{capacity_gb}GB%'
            result = session.execute(
                text("""
                    SELECT ROUND(AVG(price_eur)::numeric, 2) as avg_price, COUNT(*) as cnt
                    FROM listings
                    WHERE category = 'ssd' AND is_active = true AND title ILIKE :pat
                """),
                {"pat": title_filter}
            ).fetchone()
            if result and result[0] and result[1] >= 3:
                return float(result[0])
        fallbacks = {120: 20, 128: 22, 240: 35, 250: 35, 256: 38, 480: 60, 500: 65, 512: 65,
                     1000: 110, 1024: 110, 2000: 220, 2048: 220}
        for k in sorted(fallbacks, reverse=True):
            if capacity_gb >= k:
                return fallbacks[k]
        return 72.0

    def get_gpu_fallback_price(self, gpu_id: int) -> Optional[float]:
        with get_session() as session:
            result = session.execute(
                text("SELECT msrp_usd FROM gpu_reference WHERE id = :id"),
                {"id": gpu_id}
            ).fetchone()
            if result and result[0]:
                return round(float(result[0]) * 0.85, 2)
        return None
