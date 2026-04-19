from src.scraper.matcher import GPUMatcher, normalize_text
from src.database.connection import init_database, get_session
from src.database.repository import GPUReferenceRepository
from src.utils.config import AppConfig

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

title = "MSI Gtx 970 gaming"

# Test different VRAM values (common typo corrections)
for vram in [None, 4096, 400, 4048, 4000, 40900]:
    result = matcher.match(title, '', vram_mb=vram)
    print(f"VRAM={vram}: {result.confidence:.0%} - {result.method}")
