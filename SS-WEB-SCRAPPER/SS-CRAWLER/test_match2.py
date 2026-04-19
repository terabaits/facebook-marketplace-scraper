from src.scraper.matcher import GPUMatcher, normalize_text
from src.database.connection import init_database, get_session
from src.database.repository import GPUReferenceRepository
from src.utils.config import AppConfig
import re

config = AppConfig.from_yaml()
init_database(config.database)

with get_session() as session:
    gpus = GPUReferenceRepository.get_all(session)

matcher = GPUMatcher(gpus)

# Simulate what parser does
title = "MSI Gtx 970 gaming"
normalized = normalize_text(title)

print(f"Title: {title}")
print(f"Normalized: {normalized}")

# Check extracted tokens
from src.utils.text import extract_gpu_tokens
tokens = extract_gpu_tokens(title)
print(f"Tokens: {tokens}")

# Check Strategy 3 directly
model_matches = re.findall(r'(?:^|\D)(\d{3,4})\s*(ti|super|xt|xtx)?(?=\D|$)', normalized)
print(f"Number matches: {model_matches}")

has_rtx = 'rtx' in normalized
has_gtx = 'gtx' in normalized
has_rx = 'rx' in normalized and not has_rtx
has_nvidia = any(v in normalized for v in ['gigabyte', 'nvidia', 'geforce', 'msi', 'asrock', 'evga', 'palit', 'zotac', 'pny', 'asus'])
has_amd = any(v in normalized for v in ['amd', 'radeon', 'sapphire', 'xfx', 'powercolor'])
has_intel = any(v in normalized for v in ['intel', 'arc', 'ar '])

print(f"has_rtx: {has_rtx}, has_gtx: {has_gtx}, has_rx: {has_rx}")
print(f"has_nvidia: {has_nvidia}, has_amd: {has_amd}, has_intel: {has_intel}")

# Look at GTX 970 specifically
gtx_970 = [g for g in gpus if g.model == "GeForce GTX 970"][0]
gpu_norm = normalize_text(gtx_970.model)
print(f"\nGTX 970 normalized: {gpu_norm}")
print(f"VRAM: {gtx_970.vram_gb}")

# Check prefix match
is_nvidia_gpu = 'rtx' in gpu_norm or 'gtx' in gpu_norm or 'gt' in gpu_norm
print(f"is_nvidia_gpu: {is_nvidia_gpu}")

# Run actual match
result = matcher.match(title, '', vram_mb=4096)
print(f"\nResult: {result.confidence} ({result.confidence:.0%}) - {result.method}")
