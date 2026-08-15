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
    
    @property
    def name(self) -> str:
        """Full GPU name combining vendor and model."""
        return f"{self.vendor} {self.model}"
    
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


class RAMReference(BaseModel):
    """RAM reference data from ram.csv."""
    id: int
    name: str
    speed: str
    modules: str
    first_word_latency: Optional[float] = None
    cas_latency: Optional[int] = None
    rating: Optional[int] = None
    price: Optional[float] = None
    capacity_gb: Optional[int] = None  # Derived from name
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class GPUBenchmarkReference(BaseModel):
    """PassMark GPU benchmark reference data."""
    id: Optional[int] = None
    gpu_reference_id: Optional[int] = None
    passmark_id: str
    name: Optional[str] = None
    g3d_mark: Optional[int] = None
    g2d_mark: Optional[int] = None
    tdp_w: Optional[int] = None
    vram_mb: Optional[int] = None
    category: Optional[str] = None
    bus_interface: Optional[str] = None
    max_memory_mb: Optional[int] = None
    core_clock_mhz: Optional[int] = None
    mem_clock_mhz: Optional[int] = None
    rank: Optional[int] = None
    samples: Optional[int] = None
    price_usd: Optional[float] = None
    release_date: Optional[str] = None
    passmark_href: Optional[str] = None
    match_score: Optional[float] = None
    match_method: Optional[str] = None
    
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
    
    # Version tracking for reused IDs
    version_number: int = 1
    
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
    
    # Matching results for RAM
    matched_ram_id: Optional[int] = None
    ram_confidence_score: Optional[float] = None
    ram_match_method: Optional[str] = None
    
    # Matching results for Motherboards
    motherboard_model_id: Optional[int] = None
    motherboard_confidence_score: Optional[float] = None
    motherboard_match_method: Optional[str] = None
    
    # Bundle / combo flag
    is_special_listing: bool = False
    special_listing_reason: Optional[str] = None
    
    # Matching results for Monitors
    monitor_model_id: Optional[int] = None
    monitor_confidence_score: Optional[float] = None
    monitor_match_method: Optional[str] = None
    
    # Matching results for Lenses
    matched_lens_id: Optional[str] = None
    lens_confidence_score: Optional[float] = None
    lens_match_method: Optional[str] = None
    
    # Matching results for Cameras
    matched_camera_id: Optional[int] = None
    camera_confidence_score: Optional[float] = None
    camera_match_method: Optional[str] = None
    
    # RAM-specific extracted fields
    ram_type: Optional[str] = None  # DDR3, DDR4, DDR5
    ram_frequency_mhz: Optional[int] = None
    ram_manufacturer: Optional[str] = None
    ram_model: Optional[str] = None
    
    # Source marketplace
    source: str = "ss.com"  # 'ss.com', 'andelemandele', '1a.lv', etc.
    
    # Lifecycle
    is_active: bool = True
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Duplication detection
    content_hash: Optional[str] = None
    previous_listing_id: Optional[str] = None
    
    local_image_path: Optional[str] = None

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


class RAMMatchResult(BaseModel):
    """RAM matching result."""
    ram: Optional[RAMReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True


class CaseReference(BaseModel):
    """Case reference data from cases.csv."""
    id: int
    name: str
    type: Optional[str] = None
    color: Optional[str] = None
    power_supply: Optional[str] = None
    side_panel: Optional[str] = None
    external_volume: Optional[float] = None
    internal_35_bays: Optional[int] = None
    rating: Optional[int] = None
    price: Optional[float] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class PSUReference(BaseModel):
    """PSU reference data from psu.csv."""
    id: int
    name: str
    form_factor: Optional[str] = None
    efficiency_rating: Optional[str] = None
    wattage: Optional[int] = None
    modular: Optional[str] = None
    rating: Optional[int] = None
    price: Optional[float] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class CaseMatchResult(BaseModel):
    """Case matching result."""
    case: Optional[CaseReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True


class PSUMatchResult(BaseModel):
    """PSU matching result."""
    psu: Optional[PSUReference] = None
    confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    
    class Config:
        from_attributes = True


# Console Models
class ConsoleReference(BaseModel):
    """Console reference data."""
    model_config = {'protected_namespaces': ()}
    
    id: int
    name: str
    company: Optional[str] = None
    generation: Optional[int] = None
    release_date: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str


class ConsoleVariant(BaseModel):
    """Console variant (model) reference data."""
    model_config = {'protected_namespaces': ()}
    
    id: int
    console_id: int
    model_name: str
    sku: Optional[str] = None
    storage_gb: Optional[int] = None
    region: Optional[str] = None
    release_date: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str


class ConsoleEdition(BaseModel):
    """Console edition/special color reference data."""
    model_config = {'protected_namespaces': ()}
    
    id: int
    console_id: int
    variant_id: Optional[int] = None
    edition_name: str
    color: Optional[str] = None
    special_features: Optional[str] = None
    msrp_usd: Optional[float] = None
    msrp_eur: Optional[float] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str


class ConsoleListing(BaseModel):
    """Console listing data."""
    model_config = {'protected_namespaces': ()}
    
    id: Optional[int] = None
    listing_id: str
    version_number: int = 1  # Version for reused listing IDs
    title: str
    description: Optional[str] = None
    price_eur: float
    seller_location: Optional[str] = None
    listing_url: str
    image_url: Optional[str] = None
    local_image_path: Optional[str] = None
    date_posted: Optional[datetime] = None
    
    # Matching results
    matched_console_id: Optional[int] = None
    matched_variant_id: Optional[int] = None
    matched_edition_id: Optional[int] = None
    
    # Confidence scores
    console_confidence_score: Optional[float] = None
    console_match_method: Optional[str] = None
    variant_confidence_score: Optional[float] = None
    variant_match_method: Optional[str] = None
    edition_confidence_score: Optional[float] = None
    edition_match_method: Optional[str] = None
    
    # Special edition flag
    is_special_edition: bool = False
    special_edition_note: Optional[str] = None
    
    # Lifecycle
    is_active: bool = True
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    content_hash: Optional[str] = None
    previous_listing_id: Optional[str] = None


class LaptopListing(BaseModel):
    """Raw laptop listing data."""
    id: Optional[int] = None
    listing_id: str
    title: str
    description: Optional[str] = None
    price_eur: float
    seller_location: Optional[str] = None
    listing_url: str
    image_url: Optional[str] = None
    local_image_path: Optional[str] = None
    date_posted: Optional[datetime] = None

    # Structured fields extracted from SS.com options table
    brand: Optional[str] = None
    model: Optional[str] = None
    display_size: Optional[str] = None
    cpu_raw: Optional[str] = None
    cpu_freq_ghz: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    storage_type: Optional[str] = None
    gpu_raw: Optional[str] = None
    condition_state: Optional[str] = None

    # Lifecycle
    source: str = "ss.com"
    is_active: bool = True
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    content_hash: Optional[str] = None
    previous_listing_id: Optional[str] = None


class ConsoleMatchResult(BaseModel):
    """Console matching result."""
    model_config = {'protected_namespaces': ()}
    
    console: Optional[ConsoleReference] = None
    variant: Optional[ConsoleVariant] = None
    edition: Optional[ConsoleEdition] = None
    console_confidence: float = 0.0
    variant_confidence: float = 0.0
    edition_confidence: float = 0.0
    method: str = "none"  # none, exact, fuzzy, partial
    is_special: bool = False
    special_note: Optional[str] = None


class CameraReference(BaseModel):
    """Camera reference data from camera database."""
    id: int
    brand: str
    model: str
    model_original: Optional[str] = None
    mount: Optional[str] = None
    sensor: Optional[str] = None
    camera_type: Optional[str] = None
    category: Optional[str] = None
    release_year: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[str] = None
    iso: Optional[str] = None
    focus_points: Optional[str] = None
    video_specs: Optional[str] = None
    battery: Optional[str] = None
    storage: Optional[str] = None
    screen: Optional[str] = None
    evf: Optional[str] = None
    has_raw: bool = False
    has_clog: bool = False
    has_clog2: bool = False
    has_clog3: bool = False
    has_slog: bool = False
    has_slog2: bool = False
    has_slog3: bool = False
    has_4k: bool = False
    has_8k: bool = False
    sd_type: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class MotherboardReference(BaseModel):
    """Motherboard reference data."""
    id: int
    brand: str
    model: str
    socket: Optional[str] = None
    chipset: Optional[str] = None
    ram_slots: Optional[int] = None
    form_factor: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class MotherboardMatchResult(BaseModel):
    """Motherboard matching result."""
    motherboard: Optional[MotherboardReference] = None
    confidence: float = 0.0
    method: str = "none"
    
    class Config:
        from_attributes = True


class MonitorReference(BaseModel):
    """Monitor reference data."""
    id: int
    brand: str
    model: str
    size: Optional[str] = None
    resolution: Optional[str] = None
    refresh_rate: Optional[str] = None
    panel_type: Optional[str] = None
    search_keywords: List[str] = Field(default_factory=list)
    normalized_name: str
    
    class Config:
        from_attributes = True


class MonitorMatchResult(BaseModel):
    """Monitor matching result."""
    monitor: Optional[MonitorReference] = None
    confidence: float = 0.0
    method: str = "none"
    
    class Config:
        from_attributes = True
