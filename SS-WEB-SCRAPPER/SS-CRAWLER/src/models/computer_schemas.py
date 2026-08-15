"""Pydantic models for computer listings."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ComputerListing(BaseModel):
    """PC listing with component detection."""
    id: Optional[int] = None
    listing_id: str
    version_number: int = 1  # Version for reused listing IDs
    title: str
    description: Optional[str] = None
    price_eur: float
    seller_location: Optional[str] = None
    listing_url: str
    image_url: Optional[str] = None
    date_posted: Optional[datetime] = None
    
    # Component matches
    matched_cpu_id: Optional[int] = None
    matched_gpu_id: Optional[int] = None
    matched_ram_id: Optional[int] = None
    matched_ssd_id: Optional[int] = None
    matched_ssd2_id: Optional[int] = None  # Second SSD
    matched_ssd3_id: Optional[int] = None  # Third SSD
    matched_psu_id: Optional[int] = None
    matched_case_id: Optional[int] = None
    matched_motherboard_id: Optional[int] = None  # Motherboard
    matched_monitor_id: Optional[int] = None  # Monitor
    
    # Fallback assignments
    fallback_psu_wattage: Optional[int] = None
    fallback_case_price: Optional[float] = 15.0
    fallback_motherboard_price: Optional[float] = None
    fallback_monitor_price: Optional[float] = 100.0  # €100 default for 24" monitor
    
    # Confidence scores
    cpu_confidence: Optional[float] = None
    gpu_confidence: Optional[float] = None
    ram_confidence: Optional[float] = None
    ssd_confidence: Optional[float] = None
    ssd2_confidence: Optional[float] = None  # Second SSD confidence
    ssd3_confidence: Optional[float] = None  # Third SSD confidence
    psu_confidence: Optional[float] = None
    case_confidence: Optional[float] = None
    motherboard_confidence: Optional[float] = None  # Motherboard confidence
    monitor_confidence: Optional[float] = None  # Monitor confidence
    
    # Match methods
    cpu_match_method: Optional[str] = None
    gpu_match_method: Optional[str] = None
    ram_match_method: Optional[str] = None
    ssd_match_method: Optional[str] = None
    ssd2_match_method: Optional[str] = None  # Second SSD method
    ssd3_match_method: Optional[str] = None  # Third SSD method
    psu_match_method: Optional[str] = None
    case_match_method: Optional[str] = None
    motherboard_match_method: Optional[str] = None  # Motherboard method
    monitor_match_method: Optional[str] = None  # Monitor method
    
    # Motherboard and Monitor flags
    motherboard_detected: bool = False  # True if motherboard was detected in listing
    monitor_included: bool = False  # True if seller includes monitor with PC
    
    # Flagging
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    flag_comment: Optional[str] = None
    flagged_at: Optional[datetime] = None
    flagged_by: Optional[str] = None
    
    # Calculated totals
    components_total_eur: Optional[float] = None
    price_difference_eur: Optional[float] = None
    
    # Build type classification
    build_type: Optional[str] = None  # e.g. 'prebuilt', 'custom', 'unknown'
    is_prebuilt: bool = False
    
    # Lifecycle
    is_active: bool = True
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    content_hash: Optional[str] = None
    previous_listing_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class ComponentBreakdown(BaseModel):
    """Component breakdown with pricing for a computer listing."""
    listing_id: str
    title: str
    price_eur: float
    
    # Components
    cpu: Optional[dict] = None
    gpu: Optional[dict] = None
    ram: Optional[dict] = None
    ssd: Optional[dict] = None
    ssd2: Optional[dict] = None  # Second SSD
    ssd3: Optional[dict] = None  # Third SSD
    psu: Optional[dict] = None
    case: Optional[dict] = None
    motherboard: Optional[dict] = None
    monitor: Optional[dict] = None
    
    # Pricing
    cpu_avg_price: Optional[float] = None
    gpu_avg_price: Optional[float] = None
    ram_avg_price: Optional[float] = None
    ssd_avg_price: Optional[float] = None
    ssd2_avg_price: Optional[float] = None  # Second SSD price
    ssd3_avg_price: Optional[float] = None  # Third SSD price
    psu_avg_price: Optional[float] = None
    case_avg_price: Optional[float] = None
    motherboard_price: Optional[float] = None
    monitor_price: Optional[float] = None
    
    # Totals
    detected_total: Optional[float] = None
    fallback_total: Optional[float] = None
    grand_total: Optional[float] = None
    price_difference: Optional[float] = None
    
    class Config:
        from_attributes = True


class ComputerMatchResult(BaseModel):
    """Result of matching a computer listing to components."""
    cpu: Optional[dict] = None
    gpu: Optional[dict] = None
    ram: Optional[dict] = None
    ssd: Optional[dict] = None
    psu: Optional[dict] = None
    case: Optional[dict] = None
    motherboard: Optional[dict] = None
    monitor: Optional[dict] = None
    
    cpu_confidence: float = 0.0
    gpu_confidence: float = 0.0
    ram_confidence: float = 0.0
    ssd_confidence: float = 0.0
    psu_confidence: float = 0.0
    case_confidence: float = 0.0
    motherboard_confidence: float = 0.0
    monitor_confidence: float = 0.0
    
    cpu_method: str = "none"
    gpu_method: str = "none"
    ram_method: str = "none"
    ssd_method: str = "none"
    psu_method: str = "none"
    case_method: str = "none"
    motherboard_method: str = "none"
    monitor_method: str = "none"
    
    # Flag for monitor included
    has_monitor: bool = False
    monitor_included: bool = False  # True if monitor is explicitly part of the sale
    
    # Additional components (for listings with multiple SSDs, etc.)
    additional_ssds: Optional[list] = None
    
    class Config:
        from_attributes = True


class FlagData(BaseModel):
    """Data for flagging a computer listing."""
    is_flagged: bool = True
    flag_reason: Optional[str] = None
    flag_comment: Optional[str] = None
    flagged_by: Optional[str] = None