"""Database models for SS-Crawler."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class GPUReference(BaseModel):
    """GPU reference data from cards.csv."""
    id: int
    vendor: str
    model: str
    raw_model: Optional[str] = None
    gpu_chip: Optional[str] = None
    vram_gb: Optional[int] = None
    memory_type: Optional[str] = None
    year_released: Optional[int] = None
    msrp_usd: Optional[float] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class CPUReference(BaseModel):
    """CPU reference data from cpus.csv."""
    id: int
    producer: str
    cpu_name: str
    processor_number: str
    brand_modifier: Optional[str] = None
    generation: Optional[str] = None
    cores: Optional[int] = None
    p_cores: Optional[int] = None
    e_cores: Optional[int] = None
    threads: Optional[int] = None
    max_turbo_freq: Optional[float] = None
    base_freq: Optional[float] = None
    cache_mb: Optional[int] = None
    tdp_w: Optional[int] = None
    socket: Optional[str] = None
    integrated_graphics: Optional[str] = None
    year_released: Optional[int] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class SSDReference(BaseModel):
    """SSD reference data from SSD.csv."""
    id: int
    brand: str
    model: str
    interface: Optional[str] = None
    form_factor: Optional[str] = None
    capacity_gb: Optional[int] = None
    controller: Optional[str] = None
    configuration: Optional[str] = None
    has_dram: Optional[bool] = None
    hmb: Optional[str] = None
    nand_brand: Optional[str] = None
    nand_type: Optional[str] = None
    layers: Optional[str] = None
    read_speed_mb: Optional[int] = None
    write_speed_mb: Optional[int] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class Listing(BaseModel):
    """Scraped listing data."""
    id: Optional[int] = None
    listing_id: str
    title: str
    description: Optional[str] = None
    price_eur: float
    seller_location: Optional[str] = None
    listing_url: str
    image_url: Optional[str] = None
    date_posted: Optional[datetime] = None
    category: str = "gpu"  # 'gpu' or 'cpu' or 'ssd'
    
    # VRAM extracted from listing (in MB) - for GPU listings
    vram_mb: Optional[int] = None
    
    # Base frequency extracted from listing (in MHz) - for CPU listings  
    base_freq_mhz: Optional[int] = None
    
    # Capacity extracted from listing (in GB) - for SSD listings
    capacity_gb: Optional[int] = None
    
    # Matching results for GPU
    matched_gpu_id: Optional[int] = None
    confidence_score: Optional[float] = None
    match_method: Optional[str] = None
    
    # Matching results for CPU
    matched_cpu_id: Optional[int] = None
    cpu_confidence_score: Optional[float] = None
    cpu_match_method: Optional[str] = None
    
    # Matching results for SSD
    matched_ssd_id: Optional[int] = None
    ssd_confidence_score: Optional[float] = None
    ssd_match_method: Optional[str] = None
    
    # Lifecycle
    is_active: bool = True
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Duplication detection
    content_hash: Optional[str] = None
    previous_listing_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class PriceHistory(BaseModel):
    """Price change record."""
    id: int
    listing_id: str
    price_eur: float
    recorded_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


class ScrapeRun(BaseModel):
    """Scraping session record."""
    id: int
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    category: Optional[str] = None
    total_listings: int = 0
    new_listings: int = 0
    updated_listings: int = 0
    skipped_unchanged: int = 0
    failed_requests: int = 0
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None
    config_snapshot: Optional[dict] = None
    
    class Config:
        from_attributes = True


class DebugSnapshot(BaseModel):
    """Debug HTML snapshot."""
    id: int
    listing_id: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.now)
    html_content: str
    parse_error: Optional[str] = None
    url: Optional[str] = None
    
    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    """GPU matching result."""
    gpu: Optional[GPUReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True


class CPUMatchResult(BaseModel):
    """CPU matching result."""
    cpu: Optional[CPUReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True


class SSDMatchResult(BaseModel):
    """SSD matching result."""
    ssd: Optional[SSDReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True
