"""
Clear model_number values that are obviously not real SKUs.

Conservative: only clear values that match well-known NON-product patterns.
Real product patterns (Apple A####, Lenovo T###, Acer A###-##, etc.) are kept.
"""
import re
import psycopg2

DB_DSN = dict(host="localhost", port=5433, dbname="ss_market", user="crawler", password="crawler_pass")

# Patterns that indicate model_number is actually something OTHER than a laptop SKU
BAD_PATTERNS = [
    # WiFi card names
    r"^AX\d{3,4}$",            # Intel Wi-Fi 6/7 cards (AX211, AX201, etc)
    r"^MT\d{4}$",              # MediaTek Wi-Fi cards (MT7925, etc)
    r"^RTL\d{4}[A-Z]?$",       # Realtek Wi-Fi (RTL8723be)
    r"^QCA\d{4}$",             # Qualcomm Atheros Wi-Fi
    # Chipsets
    r"^HM\d{3}$",              # Intel chipsets (HM570)
    r"^QM\d{3}$",              # Intel mobile chipsets (QM67)
    # Ports/protocols
    r"^RS\d+$",                # RS232, RS485
    r"^USB.*$",
    r"^HDMI.*$",
    r"^Thunderbolt.*$",
    r"^DP\d*$",                # DisplayPort
    r"^VGA$",
    # GPUs (workstation/mobile)
    r"^T\d{3,4}$",             # NVIDIA T500, T550, T600
    r"^A\d{4}$",               # NVIDIA A4000, A3000
    r"^RTX\s?\d{4}[A-Za-z]?$",          # RTX 3060
    r"^GTX\s?\d{4}[A-Za-z]?$",
    r"^RX\s?\d{4}[A-Za-z]?$",
    r"^MX\d{3,4}$",            # NVIDIA MX
    # CPU patterns (these belong in cpu_reference, not laptop model)
    r"^[Ii]\d-?\d+[A-Za-z]+$",        # i5-1334U, i7-1185G7
    r"^R[3579]\s?\d+[A-Za-z]*$",      # R5 5600H
    r"^Ryzen\s.*$",
    r"^Athlon\s.*$",
    # OS / general
    r"^Windows.*$",
    r"^Linux$",
    r"^ChromeOS.*$",
    # Memory / storage
    r"^DDR\d.*$",
    r"^SSD.*$",
    r"^HDD.*$",
    r"^NVMe.*$",
    r"^M\.2.*$",
    # CPU model numbers that got captured (Intel H-series, AMD HS-series)
    r"^i\d-?\d+[A-Z]{0,3}$",           # i7-1185G7 (bare, no spaces)
    r"^\d{4,5}[A-Z]{1,3}$",            # 8750H, 8250U, 1185G7, 1360P, 8945HS
    r"^\d{4,5}[A-Z][A-Z]$",            # 8945HS, 3700U, 7530U
    r"^HD\s?\d+$",                     # Intel HD graphics (HD620, HD5500)
    r"^UHD\s?\d*$",                    # Intel UHD graphics
    r"^Iris\s.*$",                     # Intel Iris
    r"^Radeon\s.*$",                   # AMD Radeon
    r"^Vega\s?\d*$",                   # AMD Vega
    r"^GeForce\s.*$",                  # NVIDIA GeForce
    r"^Quadro\s.*$",                   # NVIDIA Quadro
    r"^RTX\s?\d+.*$",                  # RTX 3060
    r"^GTX\s?\d+.*$",                  # GTX 1650
    r"^MX\d+$",                        # NVIDIA MX
    r"^RX\s?\d+.*$",                   # AMD RX
    # Display / screen specs
    r"^\d+\.\d+\"*$",          # display size (15.6)
    r"^\d+Hz$",                # refresh rate only
    r"^\d+GHz$",               # clock speed
    r"^\d+GHz\s*$",
    # Graphics names
    r"^UHD\s?\d+.*$",          # Intel UHD graphics
    r"^Iris\s.*$",
    r"^Radeon.*$",             # GPU names (but not RX...)
    r"^GeForce.*$",
    r"^Vega.*$",
    # CPU brand prefixes
    r"^Intel\s.*$",
    r"^AMD\s.*$",
    r"^Core\s.*$",             # Intel Core
    r"^Pentium.*$",
    r"^Celeron.*$",
    r"^Atom.*$",
    r"^Snapdragon.*$",
    r"^MediaTek.*$",
    # Clock speed suffixes
    r"^\d+MHZ$",               # 3200MHZ (RAM speed)
    r"^\d+GHZ$",               # 3733GHZ
    r"^\d+MHz$",
    r"^\d+Ghz$",
    # Random / fragment
    r"^[a-z]+\d+-\d+[A-Za-z]?$",     # weird lowercase codes like "ag17-31"
    r"^[\W_]+$",                     # punctuation only
    r"^[a-z]\d+MB$",                 # like 8171MB (memory size)
    r"^\d+MB$",
    r"^\d+GB$",
    r"^\d+TB$",
    r"^\d+W$",                       # wattage
    r"^\d+Wh$",                      # battery Wh
    r"^\d+MP$",                      # megapixel
    r"^\d+MP\s.*$",
]

BAD_RX = re.compile("|".join(BAD_PATTERNS), re.IGNORECASE)


def is_bad(model_number: str, brand: str = "") -> bool:
    if not model_number:
        return True  # empty string is also bad
    s = model_number.strip()
    if not s or len(s) < 2 or len(s) > 64:
        return True
    brand_lower = brand.lower() if brand else ""

    # Apple A#### is a valid model number (A1466, A1707, A2338, etc.) — never clear.
    if brand_lower == "apple" and re.match(r"^A\d{4}$", s):
        return False
    # Apple MacBook model numbers (A1xxx-A3xxx range) are valid
    if brand_lower == "apple" and re.match(r"^A[1-3]\d{3,4}$", s):
        return False
    # Acer A####-## is a valid SKU (A515-58P, A514-53, A16-71M) — never clear.
    if brand_lower == "acer" and re.match(r"^A\d+", s):
        return False
    # Lenovo/IBM — protect known-good ThinkPad/ThinkBook/IdeaPad identifiers
    if brand_lower in ("lenovo", "lenovo/ibm"):
        # T-series: T### (4xx) or T14/T15/T16 (new naming)
        if re.match(r"^T[1-4]\d{2,3}[a-z]?$", s) or s in ("T14", "T15", "T16", "T25", "T14s", "T15s", "T16s", "T480s", "T490s", "T495", "T470S", "T480S"):
            return False
        # X-series: X### (2xx, 3xx) or X1, X12, X13, X1 Carbon, X1 Yoga, X1 Nano
        if re.match(r"^X[1-3]\d{2,3}[a-z]?$", s) or s in ("X1", "X12", "X13", "X1 Carbon", "X1 Yoga", "X1 Nano"):
            return False
        # L-series: L### (1xx-5xx)
        if re.match(r"^L[1-5]\d{2}[a-z]?$", s) or s in ("L13", "L14", "L15"):
            return False
        # P-series: P1, P14, P15, P16, P17 (new) or P### (P50-P73 old)
        if re.match(r"^P\d{1,2}[a-z]?$", s) or s in ("P1", "P14", "P14s", "P15", "P15s", "P16", "P17", "P43", "P50", "P51", "P52", "P53", "P70", "P71", "P72", "P73"):
            return False
        # E-series: E### (E14, E15, E31, E480-E595)
        if re.match(r"^E\d{1,3}[a-z]?$", s) or s in ("E14", "E15", "E16"):
            return False
        # V-series: V### (V14, V15, V130, V145, V155, V330, V510)
        if re.match(r"^V\d{2,4}[a-z]?$", s) or s in ("V14", "V15", "V17"):
            return False
        # W-series: W### (W540, W541, W701)
        if re.match(r"^W\d{3}$", s):
            return False
        # IdeaPad Y-series: Y### (Y520, Y540, Y740)
        if re.match(r"^Y\d{3}$", s):
            return False
        # G-series: G### (G510, G560, G570, G580)
        if re.match(r"^G\d{3}$", s):
            return False
        # B-series: B### (B50, B570)
        if re.match(r"^B\d{2,3}$", s):
            return False
        # Yoga specific (numeric only, when paired with Yoga model in name)
        # Not protecting bare numbers here; "Yoga 7" pattern handled in lookup table
    return bool(BAD_RX.match(s))


def main():
    conn = psycopg2.connect(**DB_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, brand, model, model_number
        FROM laptop_reference
        WHERE model_number IS NOT NULL
    """)
    rows = cur.fetchall()
    cleared = []
    for id_, brand, model, mn in rows:
        if is_bad(mn, brand):
            cleared.append((id_, brand, model, mn))
    print(f"Bad model_number candidates: {len(cleared)}")
    for c in cleared:
        print(f"  [{c[0]}] {c[1]:<12} {c[2]:<22} {c[3]!r}")

    if cleared:
        # Confirm before applying
        import sys
        if "--apply" in sys.argv:
            ids = [c[0] for c in cleared]
            cur.execute(
                "UPDATE laptop_reference SET model_number = NULL WHERE id = ANY(%s)",
                (ids,),
            )
            conn.commit()
            print(f"\nCleared {len(cleared)} bad model_numbers")
        else:
            print("\n(Dry-run. Use --apply to actually clear.)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
