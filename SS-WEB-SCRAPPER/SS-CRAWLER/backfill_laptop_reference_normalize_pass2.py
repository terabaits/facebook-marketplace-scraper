"""
Pass 2: Normalize (model, model_number) for unresolved laptop_reference rows.

Two phases:
  A. Deterministic: noise filter, known canonical splits from naming conventions.
  B. Web search: lookup unknown rows via web_search, extract canonical form.

Run modes:
  --dry-run    : show proposed changes, do not apply
  --apply      : apply changes to DB
  --phase a|b  : run only one phase
"""

import argparse
import re
import sys
import psycopg2
import json
from collections import defaultdict
from pathlib import Path

DB_DSN = dict(host="localhost", port=5433, dbname="ss_market", user="crawler", password="crawler_pass")

# --------------------------------------------------------------------------
# Phase A — deterministic rules
# --------------------------------------------------------------------------

# Noise patterns: model is junk (Windows version, WiFi card, chipset, MTM, etc.)
NOISE_PATTERNS = [
    r"^Desktop-[A-Za-z0-9]+$",           # Windows hostname
    r"^22H2$",                           # Windows 11 version
    r"^Rtl\d+[A-Za-z]+$",                # Realtek wifi card
    r"^Intel Core$",                     # CPU stored as model
    r"^[Ii]\d-?\d+[A-Za-z]+$",           # Intel CPU like I5-1334U, i7-1185G7
    r"^R[3579] ?\d+[A-Za-z]*$",           # AMD Ryzen
    r"^[A-Z]\d?-\d+[A-Z]{1,2}$",         # chipset / part like HM570
    r"^[Ll]aptop[s]?$",                  # bare "Laptop" / "Laptops"
    r"^Visi$",                           # Latvian "see"
    r"^All$",                            # Latvian "all"
    r"^Visible On$",
    r"^Любой/visus$",                    # Latvian/Russian "any"
    r"^Cits$",                           # Latvian "other" brand
    r"^Hp,? dell,? lenov(o)?$",          # multi-brand listings
    r"^C47IPM1K$",                       # garbage
    r"^DG$",                             # Dell G-series prefix typo'd
    r"^8$",                              # bare number
    r"^L0Q$",                            # LOQ typo
    r"^Rlef-[A-Za-z]+$",                 # random SKU fragment
    r"^Nbd-W[a-z]+\d?$",                 # random code
    r"^Nblb-W[a-z]+\d?[A-Za-z]?$",       # random code
    r"^MS\d+[A-Z]?\d*$",                 # MSI internal like MS16R8
    r"^B2H[Wf][A-Za-z]+-\d+[A-Z]+$",     # MSI internal like B2Hwfkg-063Nl
    r"^7[89]\d{4}[Gg]\d?$",              # Lenovo MTM like 785953G
    r"^\d{2}[A-Z][A-Z0-9]{4,6}$",        # Lenovo MTM 20EV003EMH, 20BV000BUS
    r"^\d{2}[A-Z][a-z]\d?$",             # Lenovo MTM 82C7, 82K1, 82R9, 82VG, 82XQ, 82H8, 83BF, 83JG
]

# Clear model to NULL, mark as junk in dedup_log via clean canonical
def is_noise(model: str) -> bool:
    if not model:
        return True
    m = model.strip()
    for pat in NOISE_PATTERNS:
        if re.match(pat, m):
            return True
    return False

# Brand-prefix duplicate stripping
BRAND_PREFIXES = ["Acer", "Asus", "Apple", "Dell", "HP", "Hp", "Lenovo", "MSI", "Msi", "Huawei", "Samsung"]

# Per-vendor canonical (model, model_number) lookup — verified by web searches earlier
CANONICAL = {
    # Acer
    "aspire 3": ("Aspire 3", None),
    "acer aspire 3": ("Aspire 3", None),
    "aspire": ("Aspire", None),
    "aspire 5": ("Aspire 5", None),
    "acer nitro 5": ("Nitro 5", None),
    "nitro": ("Nitro", None),
    "nitro 5": ("Nitro 5", None),
    "nitro5": ("Nitro 5", None),
    "extensa": ("Extensa", None),
    "f5-573g": ("Aspire F5", "F5-573G"),
    "n22c6": ("Chromebook", "N22C6"),
    "14cb3-431-c6wh": ("Chromebook 14", "CB3-431-C6WH"),
    "a16-71m": ("Aspire 16", "A16-71M"),
    # Apple
    "4324a": ("MacBook", None),  # likely typo
    "air": ("MacBook Air", None),
    "apple macbook": ("MacBook", None),
    "mac": ("MacBook", None),
    "macbook": ("MacBook", None),
    "macbook 12": ("MacBook", "12"),
    "macbook air": ("MacBook Air", None),
    "macbook air 13": ("MacBook Air", "13"),
    "macbook pro": ("MacBook Pro", None),
    "macbook pro 14": ("MacBook Pro", "14"),
    "macbook pro 16": ("MacBook Pro", "16"),
    "macook pro": ("MacBook Pro", None),
    "mgn63ru/a": ("MacBook Air", "MGN63RU/A"),
    "myd82ze/a": ("MacBook Air", "MYD82ZE/A"),
    "pro": ("MacBook Pro", None),
    "pro 13.3": ("MacBook Pro", "13.3"),
    "m1 pro 16”": ("MacBook Pro", "16"),
    # Asus
    "8": ("VivoBook", None),  # bare "8" likely 14/15 typo'd VivoBook
    "b5404cma": ("ExpertBook B5", "B5404CMA"),
    "expertbook": ("ExpertBook", None),
    "fx504g": ("TUF Gaming", "FX504G"),
    "fx505d": ("TUF Gaming", "FX505D"),
    "fx507ze": ("TUF Gaming", "FX507ZE"),
    "fx516pe": ("TUF Dash", "FX516PE"),
    "fx707z": ("TUF Gaming", "FX707Z"),
    "gl753v": ("ROG GL753V", "GL753V"),
    "l1500cd": ("ExpertBook L1", "L1500CD"),
    "m1605ya": ("Vivobook 16", "M1605YA"),
    "nx90jq": ("NX90JQ", "NX90JQ"),
    "rog strix": ("ROG Strix", None),
    "tuf dash": ("TUF Dash", None),
    "tuf gaming": ("TUF Gaming", None),
    "ux310uqk": ("ZenBook 13", "UX310UQK"),
    "ux3404v": ("ZenBook 14", "UX3404V"),
    "ux410u": ("ZenBook", "UX410U"),
    "ux435eg": ("ZenBook", "UX435EG"),
    "q712aqbg": ("ExpertBook", "Q712AQ"),
    "x571gt-al855t": ("X571", "GT-AL855T"),
    "x5dc": ("X5DC", "X5DC"),
    "ux482egr": ("ZenBook Duo 14", "UX482EGR"),
    "vibobook k513e": ("VivoBook", "K513E"),
    "vivibook go 15": ("Vivobook Go 15", None),
    "vivobook": ("VivoBook", None),
    "vivobook 14": ("VivoBook 14", None),
    "vivobook 15": ("VivoBook 15", None),
    "vivobook 16": ("VivoBook 16", None),
    "x200ma": ("VivoBook", "X200MA"),
    "x513ean": ("VivoBook 15", "X513EA"),
    "x551ca": ("VivoBook", "X551CA"),
    "x5dc": ("X5DC", "X5DC"),
    "zbook 14x oled": ("ZenBook 14X OLED", None),  # mis-tagged as HP
    "zenbook": ("ZenBook", None),
    "zenbook 13": ("ZenBook 13", None),
    "zenbook 14": ("ZenBook 14", None),
    # Dell — bare model numbers (need family lookup)
    "11": ("Inspiron", "11"),
    "5400": ("Latitude 5400", "5400"),
    "5500": ("Latitude 5500", "5500"),
    "14z (n411z)": ("Inspiron 14z", "N411Z"),
    "15 3510": ("Inspiron 15", "3510"),
    "3510": ("Inspiron 15", "3510"),
    "3521": ("Inspiron 15", "3521"),
    "3540": ("Inspiron 15", "3540"),
    "3558": ("Inspiron 15", "3558"),
    "3570": ("Latitude 15", "3570"),
    "3580": ("Latitude 15", "3580"),
    "5520": ("Latitude 15", "5520"),
    "5580": ("Latitude 15", "5580"),
    "7420 2in1": ("Latitude 7420", "7420 2-in-1"),
    "7490": ("Latitude 7490", "7490"),
    "dc15255": ("Inspiron 15", "DC15255"),
    "dell": (None, None),  # noise
    "g5": ("G Series", "G5"),
    "inspirion 15": ("Inspiron 15", None),
    "inspiron5406": ("Inspiron 14", "5406 2-in-1"),
    "latitude": ("Latitude", None),
    "vostro": ("Vostro", None),
    "vostro 15": ("Vostro 15", None),
    "vpstro 15": ("Vostro 15", None),
    "xps 13": ("XPS 13", None),
    # HP
    "14s-cf3028tu": ("HP 14s", "CF3028TU"),
    "14s-dq2535tu": ("HP 14s", "DQ2535TU"),
    "15-fc0062ny": ("HP 15", "FC0062NY"),
    "15-fc0xxx": ("HP 15", "FC0000"),
    "15s": ("HP 15s", None),
    "15s-fq5333ng": ("HP 15s", "FQ5333NG"),
    "15s-eq2007ny": ("HP 15s", "EQ2007NY"),
    "15s-eq2xxx": ("HP 15s", "EQ2000"),
    "155-eq1xxx": ("HP 15", "EQ1000"),
    "16-am0139nn": ("HP 16", "AM0139NN"),
    "250 g5": ("HP 250", "G5"),
    "250 g6": ("HP 250", "G6"),
    "250 g9": ("HP 250", "G9"),
    "250g7": ("HP 250", "G7"),
    "255 g8": ("HP 255", "G8"),
    "3168": ("HP 3168", "3168"),
    "430 g5": ("EliteBook 430", "G5"),
    "430 g2": ("ProBook 430", "G2"),
    "445 g8": ("ProBook 445", "G8"),
    "745 g6": ("EliteBook 745", "G6"),
    "820 g1": ("EliteBook 820", "G1"),
    "840 g1": ("EliteBook 840", "G1"),
    "840 g2": ("EliteBook 840", "G2"),
    "840 g7": ("EliteBook 840", "G7"),
    "840 g8": ("EliteBook 840", "G8"),
    "840 g3": ("EliteBook 840", "G3"),
    "840g5 i5-8250u": ("EliteBook 840", "G5"),  # HP EliteBook 840 G5 with CPU leak
    "hp 255 g10": ("HP 255", "G10"),
    "17-bs0xx": ("HP 17", "BS0XX"),
    "14-ep0xxx": ("HP 14", "EP0000"),
    "15s-fq5333ng": ("HP 15s", "FQ5333NG"),
    "850 g3": ("EliteBook 850", "G3"),
    "dv6000": ("Pavilion dv6000", "dv6000"),
    "elitebook840g3": ("EliteBook 840", "G3"),
    "f0lio 947om": ("EliteBook Folio 9470", "M"),
    "folio 1040 g3": ("EliteBook Folio 1040", "G3"),
    "gaming 3": ("Victus 15", "Gaming 3"),
    "hp": (None, None),  # noise
    "hp 15-fc0006ny": ("HP 15", "FC0006NY"),
    "hp 845 g7": ("EliteBook 845", "G7"),
    "hp envy ts": ("Envy TouchSmart", None),
    "hp laptop 15": ("HP Laptop 15", None),
    "hp omer": ("Omen", None),
    "hp soectre": ("Spectre", None),
    "laptop 15": ("HP Laptop 15", None),
    "leno": (None, None),  # noise (typo for Lenovo)
    "omnibook flip": ("HP OmniBook Flip", None),
    "omninook 5 fli": ("HP OmniBook 5 Flip", None),
    "pavilion15t-au": ("Pavilion 15t", "AU"),
    "pro 650 g8": ("EliteBook 650", "G8"),
    "probook": ("ProBook", None),
    "victus": ("Victus", None),
    # Lenovo/IBM
    "13w yoga gen2": ("ThinkPad 13w Yoga", "Gen 2"),
    "20354": ("IdeaPad", "20354"),
    "20ev003emh": ("ThinkPad", "20EV003EMH"),
    "20bv000bus": ("ThinkPad", "20BV000BUS"),
    "785953g": (None, None),  # noise
    "80ue": ("IdeaPad", "80UE"),
    "81ah": ("IdeaPad 700", "81AH"),
    "81v5": ("IdeaPad 320", "81V5"),
    "81x2": ("IdeaPad 320", "81X2"),
    "82c7": ("IdeaPad 330", "82C7"),
    "82k1": ("Legion 5", "82K1"),
    "82r9": ("ThinkBook", "82R9"),
    "82rq": ("IdeaPad 5", "82RQ"),
    "82vg": ("Legion 5", "82VG"),
    "82xq": ("IdeaPad 3", "82XQ"),
    "82h8": ("IdeaPad 3", "82H8"),
    "83bf": ("IdeaPad 3", "83BF"),
    "83hl": ("IdeaPad Gaming 3", "83HL"),  # IdeaPad Gaming 3 16IAU7 MTM
    "83jg": ("IdeaPad", "83JG"),
    "81nc": ("IdeaPad 3", "81NC"),  # MTM
    "t440p": ("ThinkPad T440p", "T440p"),
    "gaming 3": ("IdeaPad Gaming 3", None),
    "gaming 3 15ach": ("IdeaPad Gaming 3", "15ACH"),
    "ideapad": ("IdeaPad", None),
    "ideapad 1": ("IdeaPad 1", None),
    "ideapad 15": ("IdeaPad 15", None),
    "ideapad 3": ("IdeaPad 3", None),
    "ideapad 5": ("IdeaPad 5", None),
    "ideapad gaming": ("IdeaPad Gaming", None),
    "ideagaming 3": ("IdeaPad Gaming 3", None),
    "ip flex 3": ("IdeaPad Flex 3", None),
    "l0q": ("LOQ", None),
    "legion 5": ("Legion 5", None),
    "lenovo": (None, None),  # noise
    "lenovo ideapad": ("IdeaPad", None),
    "p1 gen 8": ("ThinkPad P1", "Gen 8"),
    "slim 3": ("IdeaPad Slim 3", None),
    "t14s": ("ThinkPad T14s", None),
    "t14s gen1": ("ThinkPad T14s", "Gen 1"),
    "t440s": ("ThinkPad T440s", "T440s"),
    "t450s": ("ThinkPad T450s", "T450s"),
    "t460s": ("ThinkPad T460s", "T460s"),
    "t490s": ("ThinkPad T490s", "T490s"),
    "think pad e31": ("ThinkPad E31", "E31"),
    "thinkbook 14": ("ThinkBook 14", None),
    "thinkpad": ("ThinkPad", None),
    "thinkbook14 g2": ("ThinkBook 14", "G2"),
    "thinkpadx1yoga": ("ThinkPad X1 Yoga", None),
    "x1 yoga g6": ("ThinkPad X1 Yoga", "Gen 6"),
    "x1 carbon gen8": ("ThinkPad X1 Carbon", "Gen 8"),
    "yoga 9": ("Yoga 9", None),
    # MSI
    "15 f13mg": ("Modern 15", "F13MG"),
    "bravo 15 c7v": ("Bravo 15", "C7V"),
    "cyborg 15": ("Cyborg 15", None),
    "cyborg 15 a12u": ("Cyborg 15", "A12U"),
    "ge66 raider": ("Raider GE66", None),
    "gf 65 thin ue": ("GF65 Thin", "UE"),
    "gf36": ("GF36", "GF36"),
    "gf63": ("GF63", None),
    "gf63 10sc": ("GF63", "10SC"),
    "gf63 12uc": ("GF63", "12UC"),
    "gf63 thin": ("GF63 Thin", None),
    "gf63 thn 12udx": ("GF63 Thin", "12UDX"),
    "gl65 leopard": ("GL65 Leopard", None),
    "gp72 2qe pro": ("GP72", "2QE Pro"),
    "gs65 stealth": ("GS65 Stealth", None),
    "katana": ("Katana", None),
    "katana 12": ("Katana 12", None),
    "modern 15": ("Modern 15", None),
    "modern 15b7m": ("Modern 15", "B7M"),
    "msi gf63": ("GF63", None),
    "msi modern 15": ("Modern 15", None),
    "pulse gl66": ("Pulse GL66", None),
    "pulse gl76": ("Pulse GL76", None),
    "raider ge68hx": ("Raider GE68 HX", None),
    "sword 17": ("Sword 17", None),
    "thin": ("Thin", None),
    "thin 15": ("Thin 15", None),
    "thin 15-b13ve": ("Thin 15", "B13VE"),
    "vector 16": ("Vector 16", None),
    "vector 16 hx": ("Vector 16 HX", None),
    "ms16r8": ("Thin 15", "B12VE"),  # MSI internal chassis code → Thin 15 family
    "b2hwfkg-063nl": ("Cyborg A15 AI", "B2HWFKG"),  # Belgian SKU → Cyborg A15 AI family
    # NEC (only 1)
    "cyborg 15": ("Cyborg 15", None),  # same as MSI line
    # Panasonic
    "cf-31": ("Toughbook CF-31", "CF-31"),
    "cf-xz6": ("Toughbook CF-XZ6", "CF-XZ6"),
    "fz55": ("Toughbook FZ-55", "FZ-55"),
    # Samsung
    "galaxy book 4": ("Galaxy Book 4", None),
    "galaxy book2": ("Galaxy Book 2", None),
    "np750xfg": ("Galaxy Book 4", "NP750XFG"),
    "np900x4c": ("Series 9", "NP900X4C"),
    # Sony
    "sve171g11m": ("VAIO", "SVE171G11M"),
    "vaio": ("VAIO", None),
    # "Cits" (other) — actual brands hidden
    "82vg": ("Legion 5", "82VG"),  # Lenovo
    "c47ipm1k": (None, None),  # noise
    "dg": (None, None),  # noise
    "hp omer": ("Omen", None),  # HP Omen typo
    "huawei matebok": ("MateBook", None),  # typo for MateBook
    "idealpad 3": ("IdeaPad 3", None),  # Lenovo typo
    "ideapad 1": ("IdeaPad 1", None),  # Lenovo typo
    "laptop go": ("Surface Laptop Go", None),  # Microsoft
    "magicbook pro": ("MagicBook Pro", None),  # Huawei
    "matebook 14d": ("MateBook D 14", None),  # Huawei
    "matebook 14s": ("MateBook 14s", None),  # Huawei
    "matebookd14": ("MateBook D 14", None),  # Huawei
    "redmibook 14": ("RedmiBook 14", None),  # Xiaomi
    "surface laptop": ("Surface Laptop", None),  # Microsoft
    "surface pro 4": ("Surface Pro 4", None),  # Microsoft
    "surface pro 7+": ("Surface Pro 7+", None),  # Microsoft
    "surface go2": ("Surface Go 2", None),  # Microsoft
    "teclast f6 +": ("Teclast F6 Plus", None),  # Teclast
    "thinkpad 16": ("ThinkPad 16", None),  # Lenovo
}

# Normalize a (brand, model) pair to canonical (model, model_number)
def canonicalize(brand: str, raw_model: str):
    m = (raw_model or "").strip()
    if not m:
        return None
    # Brand prefix strip
    lower = m.lower()
    brand_norm = (brand or "").lower().strip()
    # direct lookup
    if lower in CANONICAL:
        result = CANONICAL[lower]
        # If brand-specific, override
        return result
    # strip brand prefix
    for prefix in [brand, brand.lower(), brand.title(), brand.upper()] if brand else []:
        if lower.startswith(prefix.lower() + " "):
            rest = m[len(prefix)+1:].strip()
            if rest.lower() in CANONICAL:
                return CANONICAL[rest.lower()]
    return None  # not found in deterministic table


# Per-brand overrides for ambiguous names
BRAND_OVERRIDES = {
    ("HP", "gaming 3"): ("Pavilion Gaming 3", None),  # HP-specific Pavilion Gaming 3 line (older)
    ("HP", "hp envy ts"): ("Envy TouchSmart", None),
    ("HP", "hp soectre"): ("Spectre", None),
    ("HP", "spectre"): ("Spectre", None),
}


def brand_canonicalize(brand: str, raw_model: str):
    """Per-brand override applied first."""
    key = (brand, raw_model.strip().lower() if raw_model else "")
    if key in BRAND_OVERRIDES:
        return BRAND_OVERRIDES[key]
    return None


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Don't apply changes")
    ap.add_argument("--apply", action="store_true", help="Apply changes to DB")
    ap.add_argument("--phase", choices=["a", "b", "all"], default="all")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        args.dry_run = True

    conn = psycopg2.connect(**DB_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, brand, model, model_number, display_size
        FROM laptop_reference
        WHERE (model_number IS NULL OR model = '' OR model IS NULL)
    """)
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} unresolved rows")

    proposed = []   # (id, new_model, new_model_number, note)
    for id_, brand, model, mn, size in rows:
        new_model = model
        new_mn = mn
        note = ""

        # If model is empty, the real product name is in model_number
        if not model or not model.strip():
            if mn:
                # try to use model_number as the source key
                canon = canonicalize(brand, mn)
                if canon is not None:
                    nm, nn = canon
                    if nm and not (isinstance(nm, str) and nm.strip() == ""):
                        new_model = nm
                        new_mn = nn
                        note = "restore-from-mn"
            if not new_model or not new_model.strip():
                # model is empty AND can't be recovered; mark unknown
                new_model = "Unknown"
                new_mn = None
                note = "empty→Unknown"
            # Skip the rest if we already decided on an action
            if (new_model, new_mn) != (model, mn):
                proposed.append((id_, brand, model, mn, new_model, new_mn, size, note))
            continue

        # Try brand-specific override FIRST
        brand_canon = brand_canonicalize(brand, model)
        if brand_canon is not None:
            new_model, new_mn = brand_canon
            if new_model is None:
                new_model = "Unknown"
                new_mn = None
                note = "noise→Unknown"
            else:
                note = "brand-override"
        else:
            # Try canonical lookup (catches real products in noise patterns like F5-573G, 82Vg)
            canon = canonicalize(brand, model)
            if canon is not None:
                new_model, new_mn = canon
                if new_model is None:
                    new_model = "Unknown"
                    new_mn = None
                    note = "noise→Unknown"
                else:
                    note = "deterministic"
            elif is_noise(model):
                new_model = "Unknown"
                new_mn = None
                note = "noise→Unknown"
        # else: keep as-is (already canonical, but missing model_number)

        if (new_model, new_mn) != (model, mn):
            proposed.append((id_, brand, model, mn, new_model, new_mn, size, note))

    # Print summary
    by_note = defaultdict(int)
    for r in proposed:
        by_note[r[7]] += 1
    print("\nBy reason:")
    for n, c in by_note.items():
        print(f"  {n}: {c}")
    print(f"Total changes: {len(proposed)}")

    # Show first 30
    print("\nSample proposed changes:")
    for r in proposed[:30]:
        print(f"  [{r[0]}] {r[1]}: {r[2]!r} → model={r[4]!r}, number={r[5]!r} ({r[7]})")

    if args.apply and proposed:
        for id_, brand, model, mn, new_model, new_mn, size, note in proposed:
            cur.execute(
                "UPDATE laptop_reference SET model=%s, model_number=%s WHERE id=%s",
                (new_model, new_mn, id_),
            )
        conn.commit()
        print(f"\nApplied {len(proposed)} changes")
    else:
        print("\n(Dry run, no changes applied)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
