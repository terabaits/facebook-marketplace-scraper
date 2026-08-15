"""
Extract hardware specs from laptop_listings.description and propagate to
laptop_reference. Specs we look for:
  - material (plastic / aluminium / aluminum / magnesium / carbon fiber)
  - usb_count (total USB-A + USB-C ports)
  - usb_c_count (USB-C ports)
  - hdmi_count (HDMI ports)
  - has_hdmi (boolean)
  - has_video_pd_usb_c (USB-C with DisplayPort + Power Delivery)
  - has_ethernet (RJ-45 / LAN)
  - has_touchscreen
  - resolution (1920x1080, 2560x1440, etc.)

For each (brand, model, model_number, display_size) group, take the most
common non-null value across the group's descriptions. Group merge is
non-destructive: only set on the reference row when the field is currently NULL.
"""
import re
import sys
from collections import Counter
import psycopg2

DB_DSN = dict(host="localhost", port=5433, dbname="ss_market", user="crawler", password="crawler_pass")

# Compiled regex patterns
RE_USB_A = re.compile(r"\b(\d{1,2})\s*(?:x\s*)?(?:USB[\s-]?A|USB\s+\d|USB\s+Type[\s-]?A|USB[\s-]?3|USB[\s-]?2)\b", re.IGNORECASE)
RE_USB_C = re.compile(r"\b(\d{1,2})\s*(?:x\s*)?(?:USB[\s-]?C|USB[\s-]?Type[\s-]?C|Type[\s-]?C)\b", re.IGNORECASE)
RE_HDMI = re.compile(r"\b(\d{1,2})\s*(?:x\s*)?HDMI\b", re.IGNORECASE)
RE_ETHERNET = re.compile(r"\b(?:RJ[\s-]?45|Ethernet|LAN|Gigabit\s+Ethernet|10\s*/\s*100|GbE)\b", re.IGNORECASE)
RE_TOUCH = re.compile(r"\b(?:touch\s*screen|touchscreen|skārien|skarien|jūtīgais)\b", re.IGNORECASE)
RE_VIDEO_PD = re.compile(r"\b(?:USB[\s-]?C[^.\n]*?(?:DisplayPort|DP|video)[^.\n]*?(?:Power\s*Delivery|PD|charge)|DP\s*alt\s*mode|Thunderbolt\s*4[^.\n]*?PD|Thunderbolt[^.\n]*?(?:video|charge))\b", re.IGNORECASE)
RE_RESOLUTION = re.compile(r"\b(\d{3,4})\s*[xX×]\s*(\d{3,4})\b")
RE_MATERIAL = re.compile(r"\b(plastic|plastmas|plastmasa|alumini[ju]m|aluminum|magnesium|magnija|metāla|metāls|carbon\s*fiber|carbon|kohlenstoff|kevlar)\b", re.IGNORECASE)
RE_HDMI_BOOL = re.compile(r"\b(?:HDMI)\b", re.IGNORECASE)


def extract_specs(description: str) -> dict:
    """Extract all spec signals from a single description."""
    out = {}
    if not description:
        return out

    # Material
    m = RE_MATERIAL.search(description)
    if m:
        word = m.group(1).lower()
        # Normalize to DB-allowed values: 'Plastic' or 'Metal'
        plastic_words = {"plastic", "plastmas", "plastmasa"}
        metal_words = {"alumini", "aluminum", "magnesium", "magnija", "metāla", "metāls",
                       "carbon fiber", "carbon", "kohlenstoff", "kevlar", "metal"}
        if word in plastic_words:
            out["material"] = "Plastic"
        elif word in metal_words:
            out["material"] = "Metal"

    # USB-A count (take the max if multiple)
    usb_a_matches = [int(x) for x in RE_USB_A.findall(description)]
    usb_c_matches = [int(x) for x in RE_USB_C.findall(description)]
    if usb_a_matches or usb_c_matches:
        total = (max(usb_a_matches) if usb_a_matches else 0) + (max(usb_c_matches) if usb_c_matches else 0)
        if total > 0:
            out["usb_count"] = total
    if usb_c_matches:
        out["usb_c_count"] = max(usb_c_matches)

    # HDMI
    hdmi_matches = [int(x) for x in RE_HDMI.findall(description)]
    if hdmi_matches:
        out["hdmi_count"] = max(hdmi_matches)
        out["has_hdmi"] = True
    elif RE_HDMI_BOOL.search(description):
        out["has_hdmi"] = True

    # Ethernet
    if RE_ETHERNET.search(description):
        out["has_ethernet"] = True

    # Touchscreen
    if RE_TOUCH.search(description):
        out["has_touchscreen"] = True

    # Video+PD USB-C
    if RE_VIDEO_PD.search(description):
        out["has_video_pd_usb_c"] = True

    # Resolution
    res_matches = RE_RESOLUTION.findall(description)
    if res_matches:
        # Most common resolution
        cands = Counter([f"{w}x{h}" for w, h in res_matches if 800 <= int(w) <= 6000 and 600 <= int(h) <= 4000])
        if cands:
            out["resolution"] = cands.most_common(1)[0][0]

    return out


def main():
    conn = psycopg2.connect(**DB_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, brand, model, model_number, display_size,
               material, usb_count, usb_c_count, hdmi_count, resolution,
               has_hdmi, has_video_pd_usb_c, has_ethernet, has_touchscreen
        FROM laptop_reference
        WHERE model IS NOT NULL AND model <> 'Unknown'
    """)
    refs = cur.fetchall()
    print(f"Scanning {len(refs)} reference rows for spec fills")

    fields_to_set = [
        "material", "usb_count", "usb_c_count", "hdmi_count", "resolution",
        "has_hdmi", "has_video_pd_usb_c", "has_ethernet", "has_touchscreen",
    ]

    fill_counts = Counter()
    rows_updated = 0
    for ref in refs:
        id_, brand, model, model_number, size, *current_vals = ref
        # current_vals = [material, usb_count, usb_c_count, hdmi_count, resolution, has_hdmi, has_video_pd_usb_c, has_ethernet, has_touchscreen]
        # only fill NULL fields
        null_mask = [v is None for v in current_vals]
        if not any(null_mask):
            continue  # all fields already set

        # Get the descriptions for this group
        cur.execute("""
            SELECT description FROM laptop_listings
            WHERE brand = %s AND model = %s
              AND (display_size IS NOT DISTINCT FROM %s)
              AND description IS NOT NULL
        """, (brand, model, size))
        descs = [row[0] for row in cur.fetchall() if row[0]]
        if not descs:
            continue

        # Aggregate per-field winners
        new_vals = list(current_vals)
        for field in fields_to_set:
            idx = fields_to_set.index(field)
            if current_vals[idx] is not None:
                continue  # already set
            cands = Counter()
            for d in descs:
                specs = extract_specs(d)
                if field in specs:
                    cands[specs[field]] += 1
            if cands:
                new_vals[idx] = cands.most_common(1)[0][0]
                fill_counts[field] += 1

        if new_vals != list(current_vals):
            if "--apply" in sys.argv:
                cur.execute("""
                    UPDATE laptop_reference
                    SET material = %s, usb_count = %s, usb_c_count = %s,
                        hdmi_count = %s, resolution = %s,
                        has_hdmi = %s, has_video_pd_usb_c = %s,
                        has_ethernet = %s, has_touchscreen = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (*new_vals, id_))
                rows_updated += 1
            else:
                # dry run - show first 20
                pass

    if "--apply" in sys.argv:
        conn.commit()
        print(f"\nUpdated {rows_updated} reference rows")
    else:
        print(f"\n(Dry run. Use --apply to commit.)")

    print(f"\nFill breakdown (across {len(refs)} refs):")
    for field, count in fill_counts.most_common():
        print(f"  {field:<22} {count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
