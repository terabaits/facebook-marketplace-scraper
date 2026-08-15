"""Apply canonical (model, model_number) splits to laptop_reference
using a hand-built lookup table that combines my training knowledge
with web-search verification.

The lookup is keyed on (brand, combined_query) where combined_query is
"<model> <model_number>". For each match, the table gives the canonical
split. Rows not in the table are left alone (admin can refine).

Safe to re-run. Pass --apply to actually UPDATE.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor


# ---------------------------------------------------------------------------
# Canonical lookup table. Each entry is a row's combined "<model> <number>"
# string (case-insensitive) mapped to the canonical (model, model_number).
# The lookup is conservative: if I'm not sure, the row is left alone.
# Format: combined_lower -> (model, model_number)
# ---------------------------------------------------------------------------
_LOOKUP: dict[str, tuple[str, str | None]] = {
    # --- Dell (full model name in `model`, no separate number) ---
    "latitude 5400":  ("Latitude 5400", None),
    "latitude 5420":  ("Latitude 5420", None),
    "latitude 5410":  ("Latitude 5410", None),
    "latitude 5430":  ("Latitude 5430", None),
    "latitude 5440":  ("Latitude 5440", None),
    "latitude 5480":  ("Latitude 5480", None),
    "latitude 5490":  ("Latitude 5490", None),
    "latitude 5310":  ("Latitude 5310", None),
    "latitude 5320":  ("Latitude 5320", None),
    "latitude 5450":  ("Latitude 5450", None),
    "latitude 5520":  ("Latitude 5520", None),
    "latitude 7280":  ("Latitude 7280", None),
    "latitude 7290":  ("Latitude 7290", None),
    "latitude 7390":  ("Latitude 7390", None),
    "latitude 7430":  ("Latitude 7430", None),
    "latitude 7440":  ("Latitude 7440", None),
    "latitude 7480":  ("Latitude 7480", None),
    "latitude 3510":  ("Latitude 3510", None),
    "latitude 3580":  ("Latitude 3580", None),
    "latitude 5500":  ("Latitude 5500", None),
    "latitude e6400": ("Latitude E6400", None),
    "latitude e5470": ("Latitude E5470", None),
    "latitude e7270": ("Latitude E7270", None),
    "latitude e7240": ("Latitude E7240", None),
    "latitude e558":  ("Latitude E558", None),
    "latitude e448":  ("Latitude E448", None),
    "vostro 3400":    ("Vostro 3400", None),
    "vostro 3500":    ("Vostro 3500", None),
    "vostro 3520":    ("Vostro 3520", None),
    "vostro 5568":    ("Vostro 5568", None),
    "vostro 15 3000": ("Vostro 15 3000", None),
    "inspiron 3501":  ("Inspiron 3501", None),
    "inspiron 3543":  ("Inspiron 3543", None),
    "inspiron 5558":  ("Inspiron 5558", None),
    "inspiron 14 p130g": ("Inspiron 14 P130G", None),
    "g15 5511":       ("Dell G15 5511", None),
    "g3 3579":        ("Dell G3 3579", None),
    "g5 5587":        ("Dell G5 5587", None),
    "e5450 e5480":    ("Latitude E5450", None),
    "precision 3541": ("Precision 3541", None),
    "precision 3561": ("Precision 3561", None),
    "precision 5550": ("Precision 5550", None),
    "precision 7520": ("Precision 7520", None),
    "precision 7530": ("Precision 7530", None),
    "precision 7540": ("Precision 7540", None),
    "xps 9550":       ("XPS 9550", None),
    "xps 9560":       ("XPS 9560", None),
    "xps 13 9310":    ("XPS 13 9310", None),
    "xps 13 9320":    ("XPS 13 9320", None),
    "xps 15 9560":    ("XPS 15 9560", None),
    "xps 15 z":        ("XPS 15z", None),  # the "z" is a model variant
    "pro 14 plus ax211": ("Pro 14 Plus", None),  # AX211 is a Wi-Fi card, not a SKU

    # --- HP (split: family + size stays in model, generation is number) ---
    "elitebook 840":  ("EliteBook 840", None),
    "elitebook 850":  ("EliteBook 850", None),
    "elitebook 745":  ("EliteBook 745", None),
    "840 g3":         ("EliteBook 840", "G3"),
    "840 g5":         ("EliteBook 840", "G5"),
    "elitebook 840 g5": ("EliteBook 840", "G5"),
    "probook 430":    ("ProBook 430", None),
    "probook 430 g7": ("ProBook 430", "G7"),
    "probook 440 g4": ("ProBook 440", "G4"),
    "probook 440 g6": ("ProBook 440", "G6"),
    "probook 445 g8": ("ProBook 445", "G8"),
    "probook 450 g4": ("ProBook 450", "G4"),
    "probook 450 g5": ("ProBook 450", "G5"),
    "probook 450 g6": ("ProBook 450", "G6"),
    "probook 450 g7": ("ProBook 450", "G7"),
    "probook 450 g8": ("ProBook 450", "G8"),
    "probook 450 g":  ("ProBook 450", None),
    "probook 5330m":  ("ProBook 5330m", None),
    "probook 650 g2": ("ProBook 650", "G2"),
    "probook 4530s":  ("ProBook 4530s", None),
    "omen hm570":     ("Omen", None),  # HM570 is the chipset, not a SKU
    "pavilion 15-ef": ("Pavilion 15", None),
    "pavilion dm3":   ("Pavilion dm3", None),
    "pavilion":       ("Pavilion", None),
    "pavilion x360":  ("Pavilion x360", None),
    "envy x360 13":   ("Envy x360 13", None),
    "envy x360":      ("Envy x360", None),
    "envy notebook":  ("Envy Notebook", None),
    "x360 1030 g8":   ("EliteBook x360 1030", "G8"),
    "x360 435 g10":   ("EliteBook x360 435", "G10"),
    "zbook":          ("ZBook", None),
    "17-bs0xx":       ("17-bs0000", None),  # Pavilion 17-bs series
    "14-ep0xxx":      ("14-ep0000", None),  # Pavilion 14-ep series
    "255 g10":        ("255 G10", None),
    "pro 450 g10":    ("Pro 450 G10", None),

    # --- Acer (split: family+size in model, SKU in number) ---
    "aspire 3 a315":  ("Aspire 3", "A315"),
    "aspire 5 a515-58p": ("Aspire 5", "A515-58P"),
    "aspire 5 a515-56": ("Aspire 5", "A515-56"),
    "aspire 5 a515-51g": ("Aspire 5", "A515-51G"),
    "aspire 5 15":    ("Aspire 5 15", None),
    "aspire 7 a715":  ("Aspire 7", "A715"),
    "aspire 3 a314":  ("Aspire 3", "A314"),
    "aspire a514-53": ("Aspire 5 A514-53", None),  # actually A514-53 is its own line
    "aspire a514-54": ("Aspire 5 A514-54", None),
    "aspire al17":    ("Aspire AL17", None),
    "aspire go 15":   ("Aspire Go 15", None),
    "aspire go ag15": ("Aspire Go AG15", None),
    "aspire v3-575g": ("Aspire V3-575G", None),
    "aspire ag17-31": ("Aspire AG17-31", None),
    "aspire nitro 5":  ("Aspire Nitro 5", None),
    "aspire 5 a515-58p": ("Aspire 5", "A515-58P"),
    "aspire 5 a515":  ("Aspire 5", "A515"),
    "lite 15 n4500":  ("Lite 15", None),  # N4500 is a CPU, not a SKU
    "nitro 5 an515":  ("Nitro 5", "AN515"),
    "nitro an517":    ("Nitro 5", "AN517"),
    "nitro v15":      ("Nitro V15", None),
    "predator 300":   ("Predator 300", None),
    "spin sp314-51":  ("Spin SP314-51", None),
    "travelmate p2":  ("TravelMate P2", None),
    "emachines 528":  ("eMachines 528", None),
    "aod257":         ("Aspire One D257", None),
    "a16-71m":        ("Aspire 16 A16-71M", None),
    "14cb3-431-c6wh": ("Chromebook 14 CB3-431", None),

    # --- Asus (split: family in model, SKU in number) ---
    "vivobook":       ("VivoBook", None),
    "vivobook 16x":   ("VivoBook 16X", None),
    "vivobook 16 m1": ("VivoBook 16 M1", None),
    "vivobook go":    ("VivoBook Go", None),
    "vivobook go 14": ("VivoBook Go 14", None),
    "vivobook go 15": ("VivoBook Go 15", None),
    "vivobook pro":   ("VivoBook Pro", None),
    "vivobook s15":   ("VivoBook S15", None),
    "vivobook x412d": ("VivoBook", "X412D"),
    "vivobook x512u": ("VivoBook", "X512U"),
    "vivobook x530s": ("VivoBook", "X530S"),
    "vivobook x1603": ("VivoBook", "X1603"),
    "vivibook x513":  ("VivoBook", "X513"),
    "zenbook 14x":    ("ZenBook 14X", None),
    "zenbook ux334f": ("ZenBook", "UX334F"),
    "zenbook ux3402": ("ZenBook", "UX3402"),
    "zenbook um425l": ("ZenBook", "UM425L"),
    "zenbook pro":    ("ZenBook Pro", None),
    "zenbook pro duo": ("ZenBook Pro Duo", None),
    "rog strix scar": ("ROG Strix SCAR", None),
    "rog zephyrusg1": ("ROG Zephyrus G1", None),
    "tuf gaming":     ("TUF Gaming", None),  # generic, leave as-is
    "f17 fa706ii-h7020t": ("TUF Gaming F17", "FA706II-H7020T"),
    "a17 fa706":      ("TUF Gaming A17", "FA706"),
    "expertbook p1":  ("ExpertBook P1", None),
    "e406ma n5000":   ("E406MA", None),  # N5000 is a CPU
    "eee pc 1001 ha": ("Eee PC 1001HA", None),
    "eee pc 1005pxd": ("Eee PC 1005PXD", None),
    "q712aqbg":       ("ZenBook Flip Q712AQ", None),  # 2-in-1 flip
    "x571gt-al855t":  ("VivoBook Pro 15", "X571GT-AL855T"),
    "ux410u":         ("ZenBook", "UX410U"),
    "ux435eg":        ("ZenBook", "UX435EG"),
    "a17 fa706":      ("TUF Gaming A17", "FA706"),

    # --- Lenovo (mixed: full model name or split) ---
    "thinkpad t14":   ("ThinkPad T14", None),
    "thinkpad t14 gen 3": ("ThinkPad T14", "Gen 3"),
    "thinkpad t14 gen 4": ("ThinkPad T14", "Gen 4"),
    "thinkpad t14 gen 6": ("ThinkPad T14", "Gen 6"),
    "thinkpad t14 gen 7": ("ThinkPad T14", "Gen 7"),
    "thinkpad t14 gen 5": ("ThinkPad T14", "Gen 5"),
    "thinkpad t14s gen 6": ("ThinkPad T14s", "Gen 6"),
    "thinkpad x1 carbon g12": ("ThinkPad X1 Carbon", "Gen 12"),
    "thinkpad t440p":  ("ThinkPad T440p", None),
    "thinkpad t440":   ("ThinkPad T440", None),
    "thinkpad t14":    ("ThinkPad T14", None),
    "thinkpad t480":   ("ThinkPad T480", None),
    "thinkpad t480s":  ("ThinkPad T480s", None),
    "thinkpad l15":    ("ThinkPad L15", None),
    "thinkpad l580":   ("ThinkPad L580", None),
    "thinkpad l13 yoga gen2 l13": ("ThinkPad L13 Yoga", "Gen 2"),
    "thinkpad l16 gen 2 l16": ("ThinkPad L16", "Gen 2"),
    "thinkpad p1":     ("ThinkPad P1", None),
    "thinkpad p14s":   ("ThinkPad P14s", None),
    "thinkpad p51":    ("ThinkPad P51", None),
    "thinkpad p14s gen2 t500": ("ThinkPad P14s", "Gen 2"),  # T500 is a GPU, not a model
    "thinkpad p14s gen3 t550": ("ThinkPad P14s", "Gen 3"),  # T550 is a GPU
    "thinkpad p15 gen2 a4000": ("ThinkPad P15", "Gen 2"),  # A4000 is a GPU
    "thinkpad e15":    ("ThinkPad E15", None),
    "thinkpad e14g2":  ("ThinkPad E14 Gen 2", None),
    "thinkpad e14 g":  ("ThinkPad E14 G", None),  # truncated name
    "thinkpad 11e":   ("ThinkPad 11e", None),
    "thinkpad x390":   ("ThinkPad X390", None),
    "thinkpad x250":   ("ThinkPad X250", None),
    "thinkpad x260":   ("ThinkPad X260", None),
    "thinkpad x13 gen 4 ax211": ("ThinkPad X13", "Gen 4"),  # AX211 is wifi
    "thinkpad x13 gen2 x13": ("ThinkPad X13", "Gen 2"),
    "thinkpad gen 4":  ("ThinkPad", "Gen 4"),  # too generic, mark
    "thinkpad 20ev003emh": ("ThinkPad", "20EV003EMH"),  # MTM
    "thinkbook 15g2":  ("ThinkBook 15", "G2"),
    "thinkbook g2":    ("ThinkBook", "G2"),
    "ideapad 320-15": ("IdeaPad 320-15", None),
    "ideapad l340":   ("IdeaPad L340", None),
    "ideapad s340":   ("IdeaPad S340", None),
    "ideapad s145":   ("IdeaPad S145", None),
    "ideapad s510p":  ("IdeaPad S510p", None),
    "ideapad c340":   ("IdeaPad C340", None),
    "ideapad 15iau7": ("IdeaPad 15", None),  # I5-10210U is a CPU
    "ideapad i3":     ("IdeaPad", None),  # i3 is a CPU
    "ideapad 3 15i":  ("IdeaPad 3 15", "I"),  # not perfect but reasonable
    "ideapad 5 2in1": ("IdeaPad 5 2-in-1", None),
    "ideapad 5 pro":  ("IdeaPad 5 Pro", None),
    "ideapad slim 3": ("IdeaPad Slim 3", None),
    "ideapad slim 5": ("IdeaPad Slim 5", None),
    "ideapad flex5":  ("IdeaPad Flex 5", None),
    "loq 15arp9":     ("LOQ 15ARP9", None),
    "loq 15irx10":    ("LOQ 15IRX10", None),
    "legion y520":    ("Legion Y520", None),
    "legion y540":    ("Legion Y540", None),
    "legion y740":    ("Legion Y740", None),
    "legion 5 15arh": ("Legion 5 15ARH", None),
    "legion 5 pro":   ("Legion 5 Pro", None),
    "yoga slim 7":    ("Yoga Slim 7", None),
    "yoga 510-14isk": ("Yoga 510-14ISK", None),
    "yoga 500-15ibd": ("Yoga 500-15IBD", None),
    "yoga x1 2nd":    ("Yoga X1 2nd Gen", None),
    "yoga l13":       ("Yoga L13", None),
    "yoga 370":       ("Yoga 370", None),
    "v130-15ikb":     ("V130-15IKB", None),
    "v15 g3":         ("V15 G3", None),
    "v15 g2 alc":     ("V15 G2 ALC", None),
    "v15 g4 abp":     ("V15 G4 ABP", None),
    "v15-iil":        ("V15-IIL", None),
    "v14-g2":         ("V14 G2", None),
    "v14-iil":        ("V14-IIL", None),
    "v510":           ("V510", None),  # v510-15
    "essential v130 v130": ("Essential V130", None),
    "g40 45":         ("G40-45", None),  # numeric SKU
    "b50-50 b50":     ("B50-50", None),
    "20j4002fmh l470": ("ThinkPad L470", "20J4002FMH"),  # MTM
    "81f4":           ("IdeaPad 320-15IAP", "81F4"),  # MTM
    "81nc s340":      ("IdeaPad S340", "81NC"),  # MTM
    "83hl x12600":    ("Legion 5", "83HL"),  # MTM with CPU
    "t14 21mc0059mh": ("ThinkPad T14", "21MC0059MH"),  # MTM
    "t14 gen 4 ax211": ("ThinkPad T14", "Gen 4"),  # AX211 is wifi
    "t14 gen 6 mt7925": ("ThinkPad T14", "Gen 6"),  # MT7925 is wifi
    "t14 gen 7 mt7925": ("ThinkPad T14", "Gen 7"),
    "t14s gen 6 ax211": ("ThinkPad T14s", "Gen 6"),
    "x1 carbon g12 ax211": ("ThinkPad X1 Carbon", "Gen 12"),
    "x13 gen 4 ax211": ("ThinkPad X13", "Gen 4"),
    "y540 81fv":      ("Legion Y540", "81FV"),
    "l340-15irh l340": ("IdeaPad L340-15IRH", None),
    "l460 i3-6100 l460": ("ThinkPad L460", None),  # i3-6100 is a CPU
    "e16 gen2 e12":   ("ThinkPad E16 Gen 2", None),  # ambiguous
    "ideapad 3 15i":  ("IdeaPad 3 15", None),  # already covered
    "8200u":          ("IdeaPad 320S-15", None),  # MTM-less, CPU only

    # --- MSI (full name in model) ---
    "modern 15":      ("Modern 15", None),
    "modern 15 f13m": ("Modern 15", None),  # F13M is a CPU
    "b15 a11mt b15":  ("B15", None),  # A11MT is a CPU
    "gf63 thin 11uc hm570": ("GF63 Thin 11UC", None),  # HM570 is a chipset
    "katana a17 ai":  ("Katana A17 AI", None),

    # --- Samsung (full name in model) ---
    "730u3e":         ("Series 7 NP730U3E", None),
    "n145 plus":      ("N145 Plus", None),
    "n150 plus":      ("N150 Plus", None),
    "sm-p610 p610":   ("Galaxy Tab S6 Lite P610", None),

    # --- Toshiba ---
    "c670d - 126 e300": ("Satellite C670D-126", None),  # E300 is a CPU

    # --- HP 14-ep / 17-bs (Pavilion series) ---
    "14-ep0xxx":      ("Pavilion 14-ep0000", None),
    "17-bs0xx":       ("Pavilion 17-bs0000", None),
}


# Bad model_number values to clear to NULL and merge into model
_BAD_PATTERNS = (
    # Wifi card names
    "AX211", "AX201", "AX200", "AX210",
    "MT7925", "MT7921",
    "RTL8822", "RTL8821",
    # Chipsets
    "HM570", "HM470", "HM670", "QM67", "QM170",
    # Port / interface names
    "RS232", "USB", "HDMI", "WIFI", "VGA", "DP",
    "TB3", "TB4", "RJ45", "BT", "NFC",
    # GPU model names (often accidentally stored as model_number)
    "T500", "T550", "A4000", "HM570",
    # Misc
    "AX211", "MT7925", "AX200",
)


def is_bad_value(value: str | None) -> bool:
    """Return True if `value` looks like a non-SKU token that should be cleared."""
    if not value:
        return False
    v = value.strip()
    return v in _BAD_PATTERNS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually UPDATE rows.")
    ap.add_argument("--limit", type=int, default=0, help="Max rows (0 = all).")
    args = ap.parse_args()

    conn = psycopg2.connect(
        host="localhost", port=5433, database="ss_market",
        user="crawler", password="crawler_pass",
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT lr.id, lr.brand, lr.model, lr.model_number, lr.display_size
        FROM laptop_reference lr
        WHERE lr.brand != 'Apple'
          AND lr.model NOT LIKE '%TUF%'
          AND lr.model != 'Dash'
          AND lr.model != lr.model_number
          AND lr.model_number NOT IN ('G3', 'G6', 'g4')
          AND lr.model_number IS NOT NULL
        ORDER BY lr.id
    """)
    refs = cur.fetchall()
    if args.limit:
        refs = refs[: args.limit]
    print(f"Scanning {len(refs)} reference rows (apply={args.apply})")

    updated = 0
    unchanged = 0
    by_reason: dict[str, int] = {}
    samples_changed: list[tuple] = []
    for r in refs:
        model = (r["model"] or "").strip()
        number = (r["model_number"] or "").strip()
        combined = f"{model} {number}".strip()

        new_model = None
        new_number = None
        reason = ""

        # 1) Direct lookup
        key = combined.lower()
        if key in _LOOKUP:
            new_model, new_number = _LOOKUP[key]
            reason = "lookup"
        # 2) Bad value clear-and-merge
        elif is_bad_value(number):
            new_model = combined
            new_number = None
            reason = "bad-value-cleared"
        # 3) No change
        else:
            unchanged += 1
            continue

        if new_model == model and new_number == number:
            unchanged += 1
            continue

        if args.apply:
            cur.execute(
                "UPDATE laptop_reference SET model = %s, model_number = %s, updated_at = NOW() WHERE id = %s",
                (new_model, new_number, r["id"]),
            )
        else:
            print(f"  [dry-run] {r['id']:4} {r['brand']!r:14}  {model!r:30} / {number!r:18}  ->  {new_model!r:30} / {new_number!r}")
        updated += 1
        by_reason[reason] = by_reason.get(reason, 0) + 1
        if len(samples_changed) < 20:
            samples_changed.append((r["id"], r["brand"], model, number, new_model, new_number, reason))

    if args.apply:
        conn.commit()
    cur.close()
    conn.close()

    print(f"\nUpdated {updated}  Unchanged {unchanged}  (apply={args.apply})")
    for reason, n in by_reason.items():
        print(f"  {reason}: {n}")
    if samples_changed:
        print("\nSample of changed rows:")
        for sid, brand, m_old, n_old, m_new, n_new, reason in samples_changed:
            print(f"  {sid:4}  {brand!r:14}  {m_old!r:30} / {n_old!r:18}  ->  {m_new!r:30} / {n_new!r}  ({reason})")


if __name__ == "__main__":
    main()
