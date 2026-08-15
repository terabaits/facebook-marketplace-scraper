"""
Link PassMark GPU benchmark data to gpu_reference table.

Strict variant-aware matching rules:
- Suffixes must agree: XT, GTO, GS, LE, SE, Ti, Super, Mobile, Max-Q, etc.
- If PassMark name has a variant suffix (e.g., XT, Mobile, Max-Q) and the
  gpu_reference row does not, the match is rejected.
- Mobile/Max-Q PassMark entries only match gpu_reference rows that also carry
  a Mobile/Max-Q marker (which the project cards.csv generally lacks), so they
  are effectively skipped.
- Base desktop cards still match normally.

VRAM:
- gpu_reference.vram_gb stores MB values.
- PassMark vram_mb is also MB.
"""
import csv
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from src.database.connection import init_database, get_session
from src.database.repository import GPUReferenceRepository, GPUBenchmarkReferenceRepository
from src.models.schemas import GPUReference, GPUBenchmarkReference
from src.utils.config import DatabaseConfig


_GENERIC_TOKENS = {
    "amd", "ati", "nvidia", "intel", "geforce", "radeon", "graphics", "gpu", "card",
    "video", "with", "edition", "oc", "gaming", "superclocked", "dual", "evo",
    "windforce", "strix", "aorus", "ventus", "armor", "phoenix", "tuf", "rog", "rogs",
    "ftw", "sc", "xc", "ultra", "black", "white", "red", "devil", "nitro", "pulse",
    "challenger", "hellhound", "merc", "reference", "blower", "founders", "fe",
    "gddr2", "gddr3", "gddr5", "gddr6", "gddr6x", "gddr7", "ddr", "ddr2", "ddr3",
    "ddr4", "ddr5", "sdr", "sgram", "mem", "memory", "ampere", "ada", "turing",
    "pascal", "maxwell", "kepler", "fermi", "rdna", "gcn", "unified", "shader",
    "core", "processor", "nforce", "sli",
}

_NVIDIA_FAMILIES = {"geforce", "geforce2", "geforce3", "geforce4", "geforcefx", "geforcepcx",
                    "gt", "gts", "gtx", "rtx", "fx", "quadro", "nvs", "tesla", "titan"}
_AMD_FAMILIES = {"radeon", "radeonx", "radeonhd", "hd", "rx", "r9", "r7", "r5",
                 "firepro", "fireprow", "fireprov", "firepros", "fireprod", "firepror",
                 "pro", "w"}
_INTEL_FAMILIES = {"arc", "iris", "uhd", "hd"}

# Variant markers that must be present on both sides to allow a match.
_VARIANT_MARKERS = {"mobile", "mobility", "laptop", "maxq", "maxqdesign", "go"}
# Model suffixes that distinguish different SKUs.
_MODEL_SUFFIXES = {"xt", "xtx", "x2", "gto", "gs", "le", "se", "gt", "gts", "gtx", "ti", "super", "ultra", "mx", "agp"}


def is_multi_gpu_config(name: str) -> bool:
    """Return True for crossfire/dual-GPU entries like 'Radeon HD 6670 + 6670 Dual'."""
    n = name.lower()
    return "dual" in n and "+" in n


def normalize_name(name: str) -> str:
    """Normalize a GPU name for matching."""
    n = name.lower()
    n = n.replace("max-q design", "maxq").replace("max-q", "maxq").replace("max q", "maxq")
    n = re.sub(r"\b\d+\s?(gb|g|mb|m)\b", " ", n)
    # Strip parenthetical descriptors like (pascal), (maxwell), (rdna2)
    n = re.sub(r"\s*\([^)]*\)", " ", n)
    n = re.sub(
        r"\b(video card|graphics card|gpu|edition|oc|superclocked|gaming|dual|evo|"
        r"windforce|strix|aorus|gaming x|ventus|armor|phoenix|tuf|rogs|rog|ftw|"
        r"sc|xc|ultra|black|white|red devil|nitro|pulse|challenger|hellhound|merc|"
        r"reference|blower|founders|fe|mobile|laptop|notebook)\b",
        " ",
        n,
    )
    n = re.sub(r"\s+", " ", n).strip(" -")
    n = re.sub(r"[^a-z0-9]", "", n)
    return n


def canonical_tokens(name: str) -> set:
    n = normalize_name(name)
    return set(re.findall(r"[a-z0-9]+", n)) - _GENERIC_TOKENS


_SIGNIFICANT_MODEL_TOKENS = {
    "titan", "rtx", "gtx", "gts", "gt", "rx", "r9", "r7", "r5",
    "arc", "x", "xp", "black", "z", "v", "ti", "super", "xt", "xtx",
    "le", "se", "xl", "gs", "gto", "ultra", "mx", "agp", "fx", "quadro",
}


def significant_tokens(name: str) -> set:
    """Extract meaningful model tokens even when they are concatenated in a normalized name."""
    n = normalize_name(name)
    found = set()
    for token in _SIGNIFICANT_MODEL_TOKENS:
        if token in n:
            found.add(token)
    return found - _GENERIC_TOKENS


def display_name(ref: GPUReference) -> str:
    parts = [p for p in (ref.vendor, ref.model) if p]
    return " ".join(parts)


def extract_family_info(name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (family, number, suffix)."""
    n = name.lower()
    n = n.replace("max-q design", "maxq").replace("max-q", "maxq").replace("max q", "maxq")

    m = re.search(r"\b(rtx|gtx|gts|gt|fx)\s+(\d{2,5})\b", n)
    if m:
        suffix = re.search(r"\b(ti|super|se|le|xt|xtx|ultra|gs|mx)\b", n)
        return m.group(1), m.group(2), (suffix.group(1) if suffix else "")

    m = re.search(r"\b(quadro|nvs|tesla)\s+(\w*\d{3,5})\b", n)
    if m:
        return m.group(1), re.sub(r"[^0-9]", "", m.group(2)), ""

    if re.search(r"\btitan\b", n):
        # Titan cards use name tokens instead of numbers: X, Xp, Black, Z
        suffix_match = re.search(r"\btitan\s+(xp\b|x\b|black\b|z\b)", n)
        suffix = suffix_match.group(1) if suffix_match else ""
        return "titan", "", suffix

    # Older numbered GeForce, e.g. GeForce 256, GeForce2 MX 400, GeForce 7900 GTX, 7900GTX
    if re.search(r"\bgeforce\b", n):
        rest = re.sub(r".*?\bgeforce\b\s*", "", n, count=1)
        # Number may be directly followed by a suffix token (7900GTX)
        num_match = re.search(
            r"\b(\d{3,5})\s*(gtx|gs|gt|gto|gx2|xt|xtx|se|le|ultra|mx|ti|super)?\b",
            rest,
        )
        if num_match:
            number = num_match.group(1)
            suffix = num_match.group(2) or ""
            after = rest[num_match.end():]
            # also check for a spaced-out suffix after the number block
            suffix_match = re.search(
                r"\b(gtx|gs|gt|gto|gx2|x2|xt|xtx|se|le|ultra|mx|ti|super|agp)\b", after
            )
            if suffix_match and not suffix:
                suffix = suffix_match.group(1)
        else:
            number = ""
            suffix = ""
        gen_match = re.search(r"\bgeforce\s*(2|3|4|5|6|7|8|9|10)\b", n)
        gen = gen_match.group(1) if gen_match else ""
        family = f"geforce{gen}" if gen else "geforce"
        return family, number, suffix

    m = re.search(r"\b(rx|r9|r7|r5)\s+(\d{2,5})\b", n)
    if m:
        suffix = re.search(r"\b(xt|xtx|gt|g|x|m|le|se|xl)\b", n)
        return m.group(1), m.group(2), (suffix.group(1) if suffix else "")

    m = re.search(r"\b(hd)\s+(\d{3,5})\s*(x2|xt|xtx|gt|se|le|pro|agp)?\b", n)
    if m:
        return "hd", m.group(2), (m.group(3) if m.group(3) else "")

    m = re.search(r"\bfirepro\s+(w|v|s|d|r5000|r7000|r9000)?\s*(\d{3,5})\b", n)
    if m:
        prefix = (m.group(1) or "").strip()
        family = f"firepro{prefix}" if prefix else "firepro"
        return family, m.group(2), ""

    m = re.search(r"\bradeon\s+(x|hd)?\s*(\d{3,5})\b", n)
    if m:
        prefix = (m.group(1) or "").strip()
        family = f"radeon{prefix}" if prefix else "radeon"
        suffix = re.search(r"\b(x2|xt|xtx|gt|se|le|pro)\b", n)
        return family, m.group(2), (suffix.group(1) if suffix else "")

    m = re.search(r"\b(arc)\s+(a|b)?(\d{2,5})\b", n)
    if m:
        return "arc", m.group(3), ""

    m = re.search(r"\b(iris|uhd|hd)\s+graphics\s*(\d{2,5})\b", n)
    if m:
        return m.group(1), m.group(2), ""

    return None, None, None


def extract_variant_markers(name: str) -> set:
    """Return variant markers found in the name."""
    n = name.lower()
    n = n.replace("max-q design", "maxq").replace("max-q", "maxq").replace("max q", "maxq")
    n = n.replace("laptop gpu", "laptop")
    markers = set()
    for marker in _VARIANT_MARKERS:
        if marker == "go":
            # "Go" is a mobile GeForce marker; avoid matching inside "gto".
            if re.search(r"\bgo\b", n):
                markers.add(marker)
        elif marker in n:
            markers.add(marker)
    return markers


def family_group(family: str) -> Optional[str]:
    if family in _NVIDIA_FAMILIES:
        return "nvidia"
    if family in _AMD_FAMILIES:
        return "amd"
    if family in _INTEL_FAMILIES:
        return "intel"
    return None


def family_is_modern(family: str) -> bool:
    return family in {"gtx", "rtx", "rx", "arc"}


def vram_compatible(passmark_vram: Optional[int], gpu_ref_vram: Optional[int]) -> bool:
    if passmark_vram is None or passmark_vram <= 0 or gpu_ref_vram is None or gpu_ref_vram <= 0:
        return True
    if passmark_vram == gpu_ref_vram:
        return True
    ratio = max(passmark_vram, gpu_ref_vram) / max(min(passmark_vram, gpu_ref_vram), 1)
    return ratio <= 1.1


def suffixes_compatible(pm_suffix: str, ref_suffix: str) -> bool:
    """
    Require suffix agreement. Blank matches blank. Distinct suffixes like
    XT vs (blank), GTO vs GTX, GS vs Ultra, SUPER vs (blank) must not match.
    """
    pm = pm_suffix.strip().lower()
    ref = ref_suffix.strip().lower()
    if pm == ref:
        return True
    return False


def compute_model_score(
    passmark_name: str,
    passmark_vram: Optional[int],
    gpu_ref: GPUReference,
) -> Tuple[float, str]:
    ref_display = display_name(gpu_ref)

    pm_norm = normalize_name(passmark_name)
    ref_norm = normalize_name(ref_display)

    pm_family, pm_num, pm_suffix = extract_family_info(passmark_name)
    ref_family, ref_num, ref_suffix = extract_family_info(ref_display)

    pm_variants = extract_variant_markers(passmark_name)
    ref_variants = extract_variant_markers(ref_display)

    # Hard VRAM mismatch block
    if not vram_compatible(passmark_vram, gpu_ref.vram_gb):
        return 0.0, "vram_mismatch"

    # Variant marker mismatch: PassMark is Mobile/Max-Q but reference is not
    if pm_variants and not ref_variants:
        return 0.0, "variant_mismatch"

    # ------------------------------------------------------------------
    # STRONG: family + number + suffix match
    # ------------------------------------------------------------------
    if pm_family and ref_family:
        pm_group = family_group(pm_family)
        ref_group = family_group(ref_family)

        # Cross-vendor block
        if pm_group and ref_group and pm_group != ref_group:
            return 0.0, "vendor_mismatch"

        # Cross-family block for modern families
        if pm_family != ref_family and (family_is_modern(pm_family) or family_is_modern(ref_family)):
            seq = SequenceMatcher(None, pm_norm, ref_norm).ratio()
            if seq < 0.95:
                return 0.0, "family_mismatch"

        if pm_family == ref_family:
            # For number-bearing families (RX 6600, GTX 1660 etc.)
            if pm_num and ref_num and pm_num == ref_num:
                if suffixes_compatible(pm_suffix, ref_suffix):
                    base = 95.0
                    vram_bonus = 5.0 if (passmark_vram and gpu_ref.vram_gb and passmark_vram == gpu_ref.vram_gb) else 0.0
                    return min(100.0, base + vram_bonus), "strong_name"
                else:
                    # Same family + number but different suffix = different SKU.
                    seq = SequenceMatcher(None, pm_norm, ref_norm).ratio()
                    if seq >= 0.97 and passmark_vram == gpu_ref.vram_gb:
                        return min(100.0, 80.0 + seq * 10), "name_vram"
                    return 0.0, "suffix_mismatch"

            # For family-only products (Titan, some Quadro) where number is blank,
            # match on shared significant tokens (e.g. TITAN RTX vs GeForce RTX Titan),
            # suffix agreement, and compatible VRAM.
            if not pm_num and not ref_num:
                if not suffixes_compatible(pm_suffix, ref_suffix):
                    return 0.0, "suffix_mismatch"
                pm_tokens = significant_tokens(passmark_name)
                ref_tokens = significant_tokens(ref_display)
                if pm_tokens and ref_tokens:
                    overlap = pm_tokens & ref_tokens
                    token_ratio = len(overlap) / min(len(pm_tokens), len(ref_tokens))
                    if token_ratio >= 0.80 and vram_compatible(passmark_vram, gpu_ref.vram_gb):
                        # Sequence ratio is used only for score weighting here
                        vendorless_pm = re.sub(r"^(amd|ati|nvidia|intel)\s*", "", pm_norm)
                        vendorless_ref = re.sub(r"^(amd|ati|nvidia|intel)\s*", "", ref_norm)
                        seq = SequenceMatcher(None, vendorless_pm, vendorless_ref).ratio()
                        return min(100.0, 80.0 + token_ratio * 15 + seq * 5), "strong_name"
                return 0.0, "model_mismatch"

            # Same family, different number
            seq = SequenceMatcher(None, pm_norm, ref_norm).ratio()
            if seq >= 0.97 and passmark_vram == gpu_ref.vram_gb:
                return min(100.0, 70.0 + seq * 20), "name_vram"
            return 0.0, "number_mismatch"

    # ------------------------------------------------------------------
    # WEAK: fuzzy fallback, with cross-family and variant guards
    # ------------------------------------------------------------------
    seq = SequenceMatcher(None, pm_norm, ref_norm).ratio()

    if pm_family and ref_family:
        if family_is_modern(pm_family) or family_is_modern(ref_family):
            if pm_family != ref_family and seq < 0.95:
                return 0.0, "family_mismatch"

    if seq >= 0.95:
        return min(100.0, 60.0 + seq * 35), "fuzzy"

    pm_canonical = canonical_tokens(passmark_name)
    ref_canonical = canonical_tokens(ref_display)
    if pm_canonical and ref_canonical:
        overlap = pm_canonical & ref_canonical
        if ref_canonical:
            token_ratio = len(overlap) / len(ref_canonical)
            if token_ratio >= 0.70 and seq >= 0.60:
                score = min(100.0, 55.0 + token_ratio * 35 + seq * 10)
                return score, "fuzzy"

    if seq >= 0.90:
        return min(100.0, 60.0 + seq * 20), "fuzzy"

    return 0.0, "no_match"


def find_best_match(
    passmark_name: str,
    passmark_vram: Optional[int],
    gpu_refs: List[GPUReference],
) -> Optional[Tuple[GPUReference, float, str]]:
    best: Optional[Tuple[GPUReference, float, str]] = None
    for ref in gpu_refs:
        score, method = compute_model_score(passmark_name, passmark_vram, ref)
        if score < 60:
            continue
        if best is None or score > best[1]:
            best = (ref, score, method)
    return best


def link_gpu_benchmarks(csv_path: str = "gpu_benchmark_reference.csv") -> Dict[str, int]:
    config = DatabaseConfig()
    init_database(config)

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    stats = {"passmark_total": len(rows), "matched": 0, "unmatched": 0}

    with get_session() as session:
        gpu_refs = GPUReferenceRepository.get_all(session)
        print(f"[INFO] Loaded {len(gpu_refs)} gpu_reference rows")

        vram_values = [r.vram_gb for r in gpu_refs if r.vram_gb]
        if vram_values and max(vram_values) < 48:
            print("[WARN] gpu_reference.vram_gb appears to store GB values (<48). Expected MB.")

        for row in rows:
            name = row.get("name", "")
            category = (row.get("category") or "").strip()

            # Skip crossfire/dual-GPU configurations
            if is_multi_gpu_config(name):
                record = GPUBenchmarkReference(
                    gpu_reference_id=None,
                    passmark_id=row["passmark_id"],
                    name=name,
                    g3d_mark=int(row["g3d_mark"]) if row.get("g3d_mark") else None,
                    g2d_mark=int(row["g2d_mark"]) if row.get("g2d_mark") else None,
                    tdp_w=int(row["tdp_w"]) if row.get("tdp_w") else None,
                    vram_mb=None,
                    category=category or None,
                    bus_interface=row.get("bus_interface") or None,
                    max_memory_mb=int(row["max_memory_mb"]) if row.get("max_memory_mb") else None,
                    core_clock_mhz=int(row["core_clock_mhz"]) if row.get("core_clock_mhz") else None,
                    mem_clock_mhz=int(row["mem_clock_mhz"]) if row.get("mem_clock_mhz") else None,
                    rank=int(row["rank"]) if row.get("rank") else None,
                    samples=int(row["samples"]) if row.get("samples") else None,
                    price_usd=float(row["price_usd"]) if row.get("price_usd") else None,
                    release_date=row.get("release_date") or None,
                    passmark_href=row.get("passmark_href") or None,
                    match_score=None,
                    match_method="skipped_dual",
                )
                GPUBenchmarkReferenceRepository.upsert(session, record)
                stats["unmatched"] += 1
                continue

            # Skip PassMark mobile GPUs entirely
            if category.lower() == "mobile":
                record = GPUBenchmarkReference(
                    gpu_reference_id=None,
                    passmark_id=row["passmark_id"],
                    name=name,
                    g3d_mark=int(row["g3d_mark"]) if row.get("g3d_mark") else None,
                    g2d_mark=int(row["g2d_mark"]) if row.get("g2d_mark") else None,
                    tdp_w=int(row["tdp_w"]) if row.get("tdp_w") else None,
                    vram_mb=None,
                    category=category or None,
                    bus_interface=row.get("bus_interface") or None,
                    max_memory_mb=int(row["max_memory_mb"]) if row.get("max_memory_mb") else None,
                    core_clock_mhz=int(row["core_clock_mhz"]) if row.get("core_clock_mhz") else None,
                    mem_clock_mhz=int(row["mem_clock_mhz"]) if row.get("mem_clock_mhz") else None,
                    rank=int(row["rank"]) if row.get("rank") else None,
                    samples=int(row["samples"]) if row.get("samples") else None,
                    price_usd=float(row["price_usd"]) if row.get("price_usd") else None,
                    release_date=row.get("release_date") or None,
                    passmark_href=row.get("passmark_href") or None,
                    match_score=None,
                    match_method="skipped_mobile",
                )
                GPUBenchmarkReferenceRepository.upsert(session, record)
                stats["unmatched"] += 1
                continue

            try:
                vram_mb = int(row["vram_mb"]) if row.get("vram_mb") else None
            except ValueError:
                vram_mb = None

            match = find_best_match(name, vram_mb, gpu_refs)

            gpu_ref_id = None
            score = None
            method = "unmatched"

            if match:
                ref, score, method = match
                gpu_ref_id = ref.id
                stats["matched"] += 1
            else:
                stats["unmatched"] += 1

            record = GPUBenchmarkReference(
                gpu_reference_id=gpu_ref_id,
                passmark_id=row["passmark_id"],
                name=name,
                g3d_mark=int(row["g3d_mark"]) if row.get("g3d_mark") else None,
                g2d_mark=int(row["g2d_mark"]) if row.get("g2d_mark") else None,
                tdp_w=int(row["tdp_w"]) if row.get("tdp_w") else None,
                vram_mb=vram_mb,
                category=category or None,
                bus_interface=row.get("bus_interface") or None,
                max_memory_mb=int(row["max_memory_mb"]) if row.get("max_memory_mb") else None,
                core_clock_mhz=int(row["core_clock_mhz"]) if row.get("core_clock_mhz") else None,
                mem_clock_mhz=int(row["mem_clock_mhz"]) if row.get("mem_clock_mhz") else None,
                rank=int(row["rank"]) if row.get("rank") else None,
                samples=int(row["samples"]) if row.get("samples") else None,
                price_usd=float(row["price_usd"]) if row.get("price_usd") else None,
                release_date=row.get("release_date") or None,
                passmark_href=row.get("passmark_href") or None,
                match_score=round(score, 4) if score else None,
                match_method=method,
            )
            GPUBenchmarkReferenceRepository.upsert(session, record)

    print("[INFO] Linking complete:", stats)
    return stats


def export_unmatched(output_path: str = "gpu_passmark_unmatched.csv") -> None:
    config = DatabaseConfig()
    init_database(config)
    with get_session() as session:
        unmatched = GPUBenchmarkReferenceRepository.get_unmatched(session)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["passmark_id", "name", "category", "vram_mb", "g3d_mark", "samples"])
            for rec in unmatched:
                writer.writerow([rec.passmark_id, rec.name, rec.category, rec.vram_mb, rec.g3d_mark, rec.samples])
    print(f"[INFO] Exported {len(unmatched)} unmatched records to {output_path}")


if __name__ == "__main__":
    stats = link_gpu_benchmarks()
    export_unmatched()
