"""Configuration management for SS-Crawler."""
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import yaml


@dataclass
class ScraperConfig:
    """Scraper settings."""
    base_url: str = "https://www.ss.com"
    category_path: str = "/lv/electronics/computers/completing-pc/video/"  # GPU
    cpu_category_path: str = "/lv/electronics/computers/completing-pc/cpu/"
    request_timeout: int = 30
    
    # Retry configuration
    retry_attempts: int = 5
    retry_delays: List[int] = field(default_factory=lambda: [1, 2, 4, 8, 16])
    retryable_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 408, 429])
    stop_on_status: List[int] = field(default_factory=lambda: [403])
    
    # Throttling
    throttle_min: float = 1.5
    throttle_max: float = 3.5
    
    # Limits
    test_mode: bool = False
    max_listings: int = 0  # 0 = unlimited
    max_pages: int = 5  # 0 = unlimited
    save_html_samples: bool = True
    html_samples_dir: str = "logs/html_samples"
    
    # Stale detection
    stale_after_days: int = 7
    
    # Matching
    min_confidence_threshold: float = 0.70  # Skip if confidence < 70%


@dataclass
class DatabaseConfig:
    """Database connection settings."""
    host: str = "localhost"
    port: int = 5433
    name: str = "ss_market"
    user: str = "crawler"
    password: str = "crawler_pass"
    
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class ProxyConfig:
    """Proxy settings for scraping."""
    enabled: bool = False
    urls: List[str] = field(default_factory=list)
    rotation: bool = True


@dataclass
class LoggingConfig:
    """Logging settings."""
    level: str = "INFO"
    file: str = "logs/scraper_{date}.log"
    console: bool = True
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class AppConfig:
    """Complete application configuration."""
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "AppConfig":
        """Load configuration from YAML file."""
        config_path = Path(path)
        
        if not config_path.exists():
            # Return default config and create file
            config = cls()
            config.save(path)
            return config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # Build config from YAML, falling back to defaults
        scraper_data = data.get('scraper', {})
        database_data = data.get('database', {})
        proxy_data = data.get('proxy', {})
        logging_data = data.get('logging', {})
        
        return cls(
            scraper=ScraperConfig(**scraper_data),
            database=DatabaseConfig(**database_data),
            proxy=ProxyConfig(**proxy_data),
            logging=LoggingConfig(**logging_data)
        )
    
    def save(self, path: str = "config.yaml") -> None:
        """Save current configuration to YAML file."""
        import yaml
        
        config_dict = {
            'scraper': {
                'base_url': self.scraper.base_url,
                'category_path': self.scraper.category_path,
                'cpu_category_path': self.scraper.cpu_category_path,
                'request_timeout': self.scraper.request_timeout,
                'retry_attempts': self.scraper.retry_attempts,
                'retry_delays': self.scraper.retry_delays,
                'retryable_status': self.scraper.retryable_status,
                'stop_on_status': self.scraper.stop_on_status,
                'throttle_min': self.scraper.throttle_min,
                'throttle_max': self.scraper.throttle_max,
                'test_mode': self.scraper.test_mode,
                'max_listings': self.scraper.max_listings,
                'save_html_samples': self.scraper.save_html_samples,
                'html_samples_dir': self.scraper.html_samples_dir,
                'stale_after_days': self.scraper.stale_after_days,
                'min_confidence_threshold': self.scraper.min_confidence_threshold,
            },
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'name': self.database.name,
                'user': self.database.user,
                'password': self.database.password,
            },
            'proxy': {
                'enabled': self.proxy.enabled,
                'urls': self.proxy.urls,
                'rotation': self.proxy.rotation,
            },
            'logging': {
                'level': self.logging.level,
                'file': self.logging.file,
                'console': self.logging.console,
                'max_bytes': self.logging.max_bytes,
                'backup_count': self.logging.backup_count,
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
