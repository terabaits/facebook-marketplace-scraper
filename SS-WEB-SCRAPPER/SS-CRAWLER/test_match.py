from src.scraper.matcher import GPUMatcher, normalize_text
from src.database.connection import init_database, get_session
from src.database.repository import GPUReferenceRepository
from src.utils.config import AppConfig

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

# Test various title formats
for title in ['MSI Gtx 970 gaming', 'Gtx 970', 'MSI Gtx 970', 'GTX 970']:
    print(f'Testing: "{title}"')
    print(f'  Normalized: "{normalize_text(title)}"')
    result = matcher.match(title, '')
    print(f'  Matched: {result.gpu.model if result.gpu else "None"}')
    print(f'  Confidence: {result.confidence} ({result.confidence:.0%})')
    print(f'  Method: {result.method}')
    print()
