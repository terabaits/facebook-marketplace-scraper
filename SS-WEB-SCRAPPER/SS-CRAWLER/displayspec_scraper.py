"""
displayspec_scraper.py
======================
Scraper for displayspecifications.com monitor data.

Workflow:
1. Bypass the custom JS click-challenge (one-time per session, cookies saved to disk).
2. Fetch the brand page; extract all model links (`/en/model/{id}`).
3. For each model: fetch the page; parse the spec table; insert/update `monitors_additional`.

Usage:
    # Scrape Cooler Master (1 brand)
    python displayspec_scraper.py --brand-url "https://www.displayspecifications.com/en/brand/505a43"

    # Scrape a single model
    python displayspec_scraper.py --model-url "https://www.displayspecifications.com/en/model/1cba4662"

    # Scrape multiple brands from a list file (one URL per line)
    python displayspec_scraper.py --brand-list brands.txt

DB connection: hardcoded for now (matches the rest of the project). Override with
`--db-url postgresql://user:pass@host:port/dbname` if needed.
"""
import argparse
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras
from playwright.sync_api import sync_playwright, Page, BrowserContext


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_DB = dict(host="localhost", port=5433, dbname="ss_market",
                  user="crawler", password="crawler_pass")
BASE_URL = "https://www.displayspecifications.com"
COOKIE_FILE = Path(r"C:\Users\goldm\AppData\Local\Temp\ds_cookies.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
ANTI_BOT_INIT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


# ---------------------------------------------------------------------------
# Anti-bot bypass
# ---------------------------------------------------------------------------
def bypass_antibot(context: BrowserContext, page: Page) -> bool:
    """Bypass the custom JS click-challenge. Returns True if past the challenge."""
    url = page.url
    if "verify you are human" not in (page.content().lower()):
        return True
    print(f"[antibot] Clicking challenge on {url}...")
    try:
        checkbox = page.wait_for_selector(".checkbox > div", timeout=10000)
        if checkbox:
            checkbox.click()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
    except Exception as e:
        print(f"[antibot] Click failed: {e}")
        return False
    page.wait_for_timeout(2000)
    if "verify you are human" in page.content().lower():
        return False
    # Save cookies for reuse
    cookies = context.cookies()
    if cookies:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        print(f"[antibot] Saved {len(cookies)} cookies to {COOKIE_FILE}")
    return True


def load_saved_cookies(context: BrowserContext):
    """Load cookies from disk into the browser context."""
    if not COOKIE_FILE.exists():
        return False
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print(f"[antibot] Loaded {len(cookies)} cookies from {COOKIE_FILE}")
        return True
    except Exception as e:
        print(f"[antibot] Failed to load cookies: {e}")
        return False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
# Maps display-specification labels to our column names. Keys are normalized
# (lowercased, stripped of punctuation). Use this both for direct column
# writes and to collect anything we don't have a column for into extra_specs.
LABEL_TO_COLUMN = {
    # Brand/series/model
    "brand": "brand",
    "model": "model",
    "model alias": "model_alias",
    "model year": "model_year",
    # Display
    "size class": "size_class",                      # raw text "24.5 in (inches)"
    "diagonal": "diagonal_raw",                      # raw text with mm/cm/in/ft
    "width": "width_raw",                            # raw
    "height": "height_raw",                          # raw
    "panel manufacturer": "panel_manufacturer",
    "panel model": "panel_model",
    "panel type": "panel_type",
    "panel bit depth": "panel_bit_depth",
    "frc": "frc",
    "colors": "colors_raw",                          # raw
    "aspect ratio": "aspect_ratio",
    "resolution": "resolution",
    "pixel pitch": "pixel_pitch_raw",
    "pixel density": "pixel_density_raw",
    "display area": "display_area_raw",
    "backlight": "backlight",
    "srgb": "srgb_raw",
    "adobe rgb 1998": "adobe_rgb_raw",
    "dci p3": "dci_p3_raw",
    "brightness": "brightness_raw",
    "static contrast": "static_contrast",
    "horizontal viewing angle": "viewing_angle_h_raw",
    "vertical viewing angle": "viewing_angle_v_raw",
    "minimum response time": "response_time_raw",
    "coating": "coating",
    # 3D
    "3d": "has_3d",
    # Frequencies
    "vertical frequency digital": "refresh_rate_range",
    "vertical frequency analog": "refresh_rate_range_analog",
    # Power
    "110v": "voltage_110v",
    "220v": "voltage_220v",
    "alternating current frequency": "ac_frequency",
    "power consumption off": "power_off_raw",
    "power consumption sleep": "power_sleep_raw",
    "power consumption average": "power_avg_raw",
    "power consumption eco": "power_eco_raw",
    "power consumption maximum": "power_max_raw",
    # Dimensions, weight, color
    "width with stand": "width_with_stand_raw",
    "height with stand": "height_with_stand_raw",
    "depth with stand": "depth_with_stand_raw",
    "weight with stand": "weight_with_stand_raw",
    "width without stand": "width_no_stand_raw",
    "height without stand": "height_no_stand_raw",
    "depth without stand": "depth_no_stand_raw",
    "weight without stand": "weight_no_stand_raw",
    "box width": "box_width_raw",
    "box height": "box_height_raw",
    "box depth": "box_depth_raw",
    "colors offered": "colors_offered",
    # Ergonomics
    "vesa mount": "vesa_mount",
    "vesa interface": "vesa_interface",
    "removable stand": "removable_stand",
    "height adjustment": "height_adjustment",
    "landscapeportrait pivot": "pivot",
    "left right swivel": "swivel",
    "forward backward tilt": "tilt_support",
    "forward tilt": "forward_tilt_raw",
    "backward tilt": "backward_tilt_raw",
    # Camera
    "camera": "has_camera",
    # Connectivity
    "connectivity": "connectivity",
    # Features
    "features": "features",
    # Operating conditions
    "operating temperature": "operating_temp_raw",
    "operating humidity": "operating_humidity_raw",
    "storage temperature": "storage_temp_raw",
    "storage humidity": "storage_humidity_raw",
    # Accessories
    "accessories": "accessories",
    # Additional features
    "additional features": "additional_features",
}


# Number parsing: "1920 x 1080 pixels\nFull HD / 1080p" -> ("1920 x 1080", "Full HD / 1080p")
def _split_value(raw: str) -> tuple[Optional[str], Optional[str]]:
    """Split a value on newlines; return (primary, label)."""
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split("\n") if p.strip()]
    primary = parts[0] if parts else None
    label = parts[1] if len(parts) > 1 else None
    return primary, label


def _parse_number(raw: str) -> Optional[float]:
    """Extract the first number from a value like '24.5 in (inches)' or '1920 x 1080'."""
    if not raw:
        return None
    # Try decimal first
    m = re.search(r"(\d+(?:[.,]\d+)?)", raw.replace(",", "."))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _parse_int(raw: str) -> Optional[int]:
    n = _parse_number(raw)
    return int(n) if n is not None else None


def _parse_yes_no(raw: str) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    if s.startswith("yes"):
        return "Yes"
    if s.startswith("no"):
        return "No"
    return raw.strip()


def _parse_range_hz(raw: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Parse '48 Hz - 100 Hz (hertz)' -> (48, 100, '48 Hz - 100 Hz')."""
    if not raw:
        return None, None, None
    nums = re.findall(r"(\d+)\s*Hz", raw, re.IGNORECASE)
    if not nums:
        return None, None, raw.strip()
    if len(nums) == 1:
        return int(nums[0]), int(nums[0]), raw.strip()
    return int(nums[0]), int(nums[-1]), raw.strip()


def _parse_size_inches(raw: str) -> Optional[float]:
    """Extract inches from a string like '24.5 in (inches)' or '622.28 mm (millimeters) 24.4992 in (inches)'."""
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*in\s*\(inches\)", raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Fallback: convert mm to inches
    m = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*\(millimeters\)", raw, re.IGNORECASE)
    if m:
        return round(float(m.group(1)) / 25.4, 2)
    return None


def _parse_nits(raw: str) -> Optional[int]:
    """Extract cd/m² from '250 cd/m² (candela per square meter)'."""
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*cd", raw, re.IGNORECASE)
    return int(float(m.group(1))) if m else None


def _parse_pct(raw: str) -> Optional[float]:
    """Extract percent value from '109 % (percent)'."""
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", raw, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_resolution(raw: str) -> tuple[Optional[str], Optional[str]]:
    """Parse '1920 x 1080 pixels\nFull HD / 1080p' -> ('1920 x 1080', 'Full HD / 1080p')."""
    return _split_value(raw)


def _parse_response_ms(raw: str) -> Optional[float]:
    """Parse '4 ms (milliseconds)' or '0.0040 s (seconds)' -> 4.0 ms."""
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*ms", raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*s\s*\(seconds\)", raw, re.IGNORECASE)
    if m:
        return round(float(m.group(1)) * 1000, 2)
    return None


def _parse_kg(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg", raw, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_w(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*W", raw, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_mm(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*mm", raw, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_ppi(raw: str) -> Optional[int]:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*ppi", raw, re.IGNORECASE)
    return int(float(m.group(1))) if m else None


def _parse_tilt_deg(raw: str) -> Optional[int]:
    if not raw:
        return None
    m = re.search(r"(\d+)\s*°", raw)
    return int(m.group(1)) if m else None


def _extract_label_text(td) -> tuple[str, str]:
    """Extract the LABEL and DESCRIPTION text from a <td>.

    The spec table has rows like:
        <td>Weight<p>Weight without stand in different measurement units.</p></td>
    The label is "Weight"; the <p> is a tooltip description.

    The same label can appear with different <p> descriptions (e.g. "Colors"
    means the color count for one row and "colors offered" for another). The
    description is the disambiguator. Returns (label, description_lower).
    """
    from bs4 import NavigableString
    label_parts = []
    desc_parts = []
    seen_p = False
    for child in td.children:
        name = getattr(child, "name", None)
        if name == "p":
            seen_p = True
            desc_parts.append(child.get_text(" ", strip=True))
            continue
        if seen_p:
            continue
        if isinstance(child, NavigableString):
            label_parts.append(str(child))
    label = "".join(label_parts).strip()
    desc = " ".join(desc_parts).strip().lower()
    return label, desc


def parse_model_page(html: str, model_url: str, brand_url: str) -> dict:
    """Parse a model page HTML into a dict ready for INSERT."""
    out = {
        "source_url": model_url,
        "source_id": model_url.rstrip("/").split("/")[-1],
        "brand_url": brand_url,
        "brand_id": brand_url.rstrip("/").split("/")[-1] if brand_url else None,
    }
    if not html:
        out["scrape_status"] = "failed"
        out["scrape_error"] = "empty HTML"
        return out

    # Use BeautifulSoup if available; fall back to regex
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.model-information-table tr")
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            label, desc = _extract_label_text(tds[0])
            if not label:
                continue
            label = label.rstrip(":").strip()
            # Take the second td and join all text (it may include <br>)
            value = tds[1].get_text("\n", strip=True)
            yield_row(out, label, value, desc)
    except ImportError:
        # Regex fallback: each row is `<td>Label</td><td>Value</td>`
        for m in re.finditer(
            r'<td>\s*([^<]+?)\s*<.*?</td>\s*<td>\s*(.*?)\s*</td>', html, re.DOTALL
        ):
            label = re.sub(r"\s+", " ", m.group(1)).strip()
            value = re.sub(r"<[^>]+>", " ", m.group(2))
            value = re.sub(r"\s+", " ", value).strip()
            # Regex path can't read <p>; treat desc as empty
            yield_row(out, label, value, "")

    out["scrape_status"] = "ok"
    return out


def yield_row(out: dict, label: str, value: str, desc: str = ""):
    """Dispatch a single label/value pair into the right column on `out`.

    `desc` is the lowercase <p> description text from the label cell, used to
    disambiguate rows that share the same label (e.g. "Colors" can mean the
    color count or the offered chassis color; "Weight" can be with or without
    stand).
    """
    if not label:
        return
    key = label.lower().strip()
    key_norm = re.sub(r"[^a-z0-9]+", " ", key).strip()
    # exact match (allow some whitespace variants)
    col = LABEL_TO_COLUMN.get(key_norm)

    # Stash raw into extra_specs for everything we recognize
    extra = out.setdefault("extra_specs", {})
    if col:
        extra[col] = value

    # Disambiguation: "Colors" (count) vs "Colors" (offered chassis color).
    # The count row's <p> mentions "maximum number of colors" or similar;
    # the offered row's <p> mentions "in which the specific model is offered
    # to the market". We check the description first, falling back to the
    # value's structure.
    is_colors_count = "maximum number of colors" in desc
    is_colors_offered = "offered to the market" in desc or "colors offered" in key_norm

    # Disambiguation: "Weight" (without stand) vs "Weight with stand".
    # The without-stand <p> explicitly says "Weight without stand".
    is_weight_no_stand = "without stand" in desc
    is_weight_with_stand = "with stand" in desc or "with stand" in key_norm

    # Brand
    if key_norm == "brand" and not out.get("brand"):
        out["brand"] = value
    elif key_norm == "model" and not out.get("model"):
        out["model"] = value.split("(")[0].strip()
    elif key_norm == "model alias":
        out["model_alias"] = value
    elif key_norm == "model year":
        out["model_year"] = _parse_int(value)
    # Size
    elif key_norm in ("size class", "diagonal"):
        if not out.get("size_inches"):
            n = _parse_size_inches(value)
            if n is not None:
                out["size_inches"] = n
    elif key_norm == "width" and not out.get("width_mm"):
        n = _parse_mm(value)
        if n is not None:
            out["width_mm"] = n
    elif key_norm == "height" and not out.get("height_mm"):
        n = _parse_mm(value)
        if n is not None:
            out["height_mm"] = n
    elif key_norm == "panel manufacturer":
        out["panel_manufacturer"] = value
    elif key_norm == "panel model":
        out["panel_model"] = value
    elif key_norm == "panel type":
        out["panel_type"] = value
    elif key_norm == "panel bit depth":
        out["panel_bit_depth"] = value
    elif key_norm == "frc":
        out["frc"] = _parse_yes_no(value)
    elif key_norm == "colors":
        # Two "Colors" rows: count (numeric, e.g. "16777216 colors\n24 bits")
        # and offered (text, e.g. "Black"). Disambiguate via <p> description,
        # then fall back to value inspection.
        primary, label = _split_value(value)
        if is_colors_offered and not is_colors_count:
            out["colors_offered"] = value
            extra["colors_offered"] = value
        elif is_colors_count or (primary and primary[:32].strip().isdigit()):
            # Extract the integer count from the first line
            first = (primary or "").strip()
            m = re.match(r"(\d+)", first)
            if m:
                out["colors"] = int(m.group(1))
            # And the bit depth from the second line ("24 bits")
            if label:
                bm = re.match(r"(\d+)\s*bits?", label, re.IGNORECASE)
                if bm:
                    out["colors_bits"] = int(bm.group(1))
        else:
            # Bare-text value (e.g. "Black") - treat as offered color
            out["colors_offered"] = value
            extra["colors_offered"] = value
    elif key_norm == "aspect ratio":
        out["aspect_ratio"] = value.split("\n")[0].strip()
    elif key_norm == "resolution":
        primary, label = _parse_resolution(value)
        out["resolution"] = primary
        out["resolution_label"] = label
    elif key_norm == "pixel pitch":
        out["pixel_pitch_mm"] = _parse_number(value)
    elif key_norm == "pixel density":
        out["pixel_density_ppi"] = _parse_ppi(value)
    elif key_norm == "display area":
        out["display_area_pct"] = _parse_pct(value)
    elif "vertical frequency" in key_norm:
        mn, mx, txt = _parse_range_hz(value)
        out["refresh_rate_min"] = mn
        out["refresh_rate_max"] = mx
        out["refresh_rate_range"] = txt
    elif key_norm == "backlight":
        out["backlight"] = value
    elif key_norm == "srgb":
        out["srgb_pct"] = _parse_pct(value)
    elif "adobe rgb" in key_norm:
        out["adobe_rgb_pct"] = _parse_pct(value)
    elif "dci p3" in key_norm:
        out["dci_p3_pct"] = _parse_pct(value)
    elif key_norm == "brightness":
        n = _parse_nits(value)
        if n is not None:
            out["nits"] = n
            out["brightness_cd_m2"] = n
    elif key_norm == "static contrast":
        out["static_contrast"] = value.split("\n")[0].strip()
    elif "horizontal viewing" in key_norm:
        out["viewing_angle_h"] = _parse_int(value)
    elif "vertical viewing" in key_norm:
        out["viewing_angle_v"] = _parse_int(value)
    elif "response time" in key_norm:
        out["response_time_ms"] = _parse_response_ms(value)
    elif key_norm == "coating":
        out["coating"] = value
    elif key_norm == "3d":
        out["has_3d"] = _parse_yes_no(value)
    elif key_norm == "110v":
        out["voltage_110v"] = value
    elif key_norm == "220v":
        out["voltage_220v"] = value
    elif "alternating current" in key_norm:
        out["ac_frequency"] = value
    elif "power consumption off" in key_norm:
        out["power_off_w"] = _parse_w(value)
    elif "power consumption sleep" in key_norm:
        out["power_sleep_w"] = _parse_w(value)
    elif "power consumption" in key_norm and "maximum" in key_norm:
        out["power_max_w"] = _parse_w(value)
    elif key_norm == "weight" and (is_weight_no_stand or is_weight_with_stand):
        # The bare "Weight" label appears for WITHOUT-stand on this site; the
        # WITH-stand row uses "Weight with stand". Disambiguate by <p>.
        if is_weight_no_stand:
            out["weight_no_stand_kg"] = _parse_kg(value)
        else:
            out["weight_with_stand_kg"] = _parse_kg(value)
    elif "width with stand" in key_norm:
        out["width_with_stand_mm"] = _parse_mm(value)
    elif "height with stand" in key_norm:
        out["height_with_stand_mm"] = _parse_mm(value)
    elif "depth with stand" in key_norm:
        out["depth_with_stand_mm"] = _parse_mm(value)
    elif "weight with stand" in key_norm:
        out["weight_with_stand_kg"] = _parse_kg(value)
    elif "width" in key_norm and "without stand" in key_norm:
        out["width_no_stand_mm"] = _parse_mm(value)
    elif "height" in key_norm and "without stand" in key_norm:
        out["height_no_stand_mm"] = _parse_mm(value)
    elif "depth" in key_norm and "without stand" in key_norm:
        out["depth_no_stand_mm"] = _parse_mm(value)
    elif "weight" in key_norm and "without stand" in key_norm:
        out["weight_no_stand_kg"] = _parse_kg(value)
    elif "box width" in key_norm:
        out["box_width_mm"] = _parse_mm(value)
    elif "box height" in key_norm:
        out["box_height_mm"] = _parse_mm(value)
    elif "box depth" in key_norm:
        out["box_depth_mm"] = _parse_mm(value)
    elif "colors" in key_norm and "offered" in key_norm:
        out["colors_offered"] = value
    elif "vesa mount" in key_norm:
        out["vesa_mount"] = _parse_yes_no(value)
    elif "vesa interface" in key_norm:
        out["vesa_interface"] = value
    elif "removable stand" in key_norm:
        out["removable_stand"] = _parse_yes_no(value)
    elif "height adjustment" in key_norm:
        out["height_adjustment"] = _parse_yes_no(value)
    elif "pivot" in key_norm:
        out["pivot"] = _parse_yes_no(value)
    elif "swivel" in key_norm:
        out["swivel"] = _parse_yes_no(value)
    elif "tilt" in key_norm and "forward" not in key_norm and "backward" not in key_norm:
        out["tilt_support"] = _parse_yes_no(value)
    elif "forward tilt" in key_norm:
        out["forward_tilt_deg"] = _parse_tilt_deg(value)
    elif "backward tilt" in key_norm:
        out["backward_tilt_deg"] = _parse_tilt_deg(value)
    elif key_norm == "camera":
        out["has_camera"] = _parse_yes_no(value)
    elif key_norm == "connectivity":
        out["connectivity"] = value
        _parse_connectivity(out, value)
    elif key_norm == "features":
        out["features"] = value
        _parse_features(out, value)
    elif "operating temperature" in key_norm:
        out["operating_temp_c"] = value
    elif "operating humidity" in key_norm:
        out["operating_humidity_pct"] = value
    elif "storage temperature" in key_norm:
        out["storage_temp_c"] = value
    elif "storage humidity" in key_norm:
        out["storage_humidity_pct"] = value
    elif key_norm == "accessories":
        out["accessories"] = value
    elif "additional features" in key_norm:
        out["additional_features"] = value


# ---------------------------------------------------------------------------
# Connectivity parser: split "1 x HDMI 2.0\n1 x D-sub\n1 x 3.5 mm Audio Out"
# into per-port count + version columns.
# ---------------------------------------------------------------------------
_PORT_PATTERNS = [
    # (regex, port_key, version_group_idx)
    (re.compile(r"(\d+)\s*x\s*HDMI\s*([\d\.]+)?", re.IGNORECASE), "hdmi", 2),
    (re.compile(r"(\d+)\s*x\s*(?:DisplayPort|DP)\s*([\d\.]+)?", re.IGNORECASE), "dp", 2),
    (re.compile(r"(\d+)\s*x\s*(?:D[\-\s]?sub|VGA)", re.IGNORECASE), "vga", None),
    (re.compile(r"(\d+)\s*x\s*(?:DVI[\-\s]?[DDI]?)\s*([\w\-\+]*)", re.IGNORECASE), "dvi", 2),
    (re.compile(r"(\d+)\s*x\s*(?:USB[\-\s]?C|Type[\-\s]?C)", re.IGNORECASE), "usb_c", None),
    (re.compile(r"(\d+)\s*x\s*USB\s*([\d\.]+)?", re.IGNORECASE), "usb", 2),
    (re.compile(r"(\d+)\s*x\s*(?:Thunderbolt)", re.IGNORECASE), "thunderbolt", None),
    (re.compile(r"(\d+)\s*x\s*(?:3\.5\s*mm\s*)?Audio\s*Out", re.IGNORECASE), "audio_out", None),
    (re.compile(r"(\d+)\s*x\s*(?:3\.5\s*mm\s*)?Audio\s*In", re.IGNORECASE), "audio_in", None),
    (re.compile(r"(\d+)\s*x\s*(?:3\.5\s*mm)", re.IGNORECASE), "audio_3_5mm", None),
    (re.compile(r"(\d+)\s*x\s*(?:RJ[\-\s]?45|Ethernet|LAN)", re.IGNORECASE), "rj45", None),
    (re.compile(r"(\d+)\s*x\s*(?:MHL)", re.IGNORECASE), "mhl", None),
    (re.compile(r"(\d+)\s*x\s*(?:Mini[\-\s]?HDMI)", re.IGNORECASE), "mini_hdmi", None),
    (re.compile(r"(\d+)\s*x\s*(?:Micro[\-\s]?HDMI)", re.IGNORECASE), "micro_hdmi", None),
]


def _parse_connectivity(out: dict, value: str):
    """Parse connectivity string into per-port count + version columns.

    Stores columns like: port_hdmi_count, port_hdmi_max_version,
    port_dp_count, port_dp_max_version, port_vga_count, port_usb_c_count.
    """
    if not value:
        return
    counts: dict[str, int] = {}
    versions: dict[str, list[str]] = {}
    for line in value.split("\n"):
        line = line.strip()
        if not line:
            continue
        for pat, key, ver_idx in _PORT_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            n = int(m.group(1))
            counts[key] = counts.get(key, 0) + n
            if ver_idx and m.group(ver_idx):
                versions.setdefault(key, []).append(m.group(ver_idx).strip())
            break  # first matching port type per line
    for k, n in counts.items():
        out[f"port_{k}_count"] = n
    for k, vs in versions.items():
        # Pick the highest version seen (lexicographic on string suffices for now)
        out[f"port_{k}_max_version"] = max(vs, key=lambda v: tuple(int(x) for x in re.findall(r"\d+", v) or [0]))


# ---------------------------------------------------------------------------
# Features parser: split newline-separated feature list into boolean flags.
# ---------------------------------------------------------------------------
# (substring to look for in feature line, column name on `out`)
# Use lowercase substring matches against each non-empty line.
_FEATURE_FLAGS = [
    ("hdr ready", "feature_hdr_ready"),
    ("hdr 10", "feature_hdr10"),  # matches "HDR10", "HDR 10"
    ("hdr 400", "feature_hdr400"),
    ("hdr 600", "feature_hdr600"),
    ("hdr 1000", "feature_hdr1000"),
    ("hdr 1400", "feature_hdr1400"),
    ("hdr 2000", "feature_hdr2000"),
    ("true black 400", "feature_true_black_400"),
    ("true black 500", "feature_true_black_500"),
    ("dolby vision", "feature_dolby_vision"),
    ("freesync premium pro", "feature_freesync_premium_pro"),
    ("freesync premium", "feature_freesync_premium"),
    ("freesync", "feature_freesync"),
    ("g-sync", "feature_gsync"),
    ("adaptive-sync", "feature_adaptive_sync"),
    ("flicker-free", "feature_flicker_free"),
    ("low blue light", "feature_low_blue_light"),
    ("built-in speakers", "feature_built_in_speakers"),
    ("speakers", "feature_speakers"),
    ("kvm", "feature_kvm"),
    ("picture-in-picture", "feature_pip"),
    ("picture-by-picture", "feature_pbp"),
    ("crosshair", "feature_crosshair"),
    ("fps counter", "feature_fps_counter"),
    ("black stabilizer", "feature_black_stabilizer"),
    ("dynamic overdrive", "feature_dynamic_overdrive"),
    ("motion clearness", "feature_motion_clearness"),
    ("rgb lighting", "feature_rgb_lighting"),
    ("rgb", "feature_rgb"),  # fallback
    ("overdrive", "feature_overdrive"),
    ("eye saver", "feature_eye_saver"),
    ("usb-c charging", "feature_usb_c_charging"),
    ("power delivery", "feature_power_delivery"),
    ("swivel", "feature_swivel"),
    ("pivot", "feature_pivot"),
    ("height adjustable", "feature_height_adjustable"),
    ("tilt", "feature_tilt"),
    ("vesa", "feature_vesa"),
    ("wall mount", "feature_wall_mount"),
]


def _parse_features(out: dict, value: str):
    """Parse the newline-separated features list into boolean flag columns.

    Each line is checked against the FEATURE_FLAGS list; first match wins.
    """
    if not value:
        return
    lines = [ln.strip().lower() for ln in value.split("\n") if ln.strip()]
    for ln in lines:
        for needle, col in _FEATURE_FLAGS:
            if needle in ln:
                out[col] = True
                break


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
def upsert_model(conn, data: dict) -> bool:
    """Insert or update a model row by source_id. Returns True on success."""
    if not data.get("source_id"):
        return False
    cols = [k for k in data.keys() if k != "id"]
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    update_set = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c not in ("source_id",)])
    sql = f"""
        INSERT INTO monitors_additional ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (source_id) DO UPDATE SET {update_set}
    """
    vals = []
    for c in cols:
        v = data.get(c)
        # JSONB-encode extra_specs
        if c == "extra_specs" and v is not None and not isinstance(v, (str, bytes)):
            v = json.dumps(v, ensure_ascii=False)
        vals.append(v)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, vals)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[db] UPSERT failed for {data.get('source_id')}: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def get_brand_page_model_links(page: Page, brand_url: str,
                                 include_tv: bool = False) -> list[dict]:
    """Return absolute model URLs from a brand page, each with parsed size.

    Each item is {"href": str, "size": float|None, "model": str|None,
                  "section": str} — the section header the link came from
                  (e.g. "LG - 2026 - Desktop monitors" or "LG - 2026 - TVs").

    The brand page groups models under `<header class="section-header">`
    blocks. Each block's <h1> reads either "... - Desktop monitors" or
    "... - TVs" (or "Monitors", "TVs" on some sites). We only collect links
    from monitor sections by default; pass include_tv=True to also include
    the TV sections.

    The size is parsed from the link text (e.g. "27\\" 27U730B" → 27.0).
    """
    page.goto(brand_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    sections = page.evaluate("""
        () => {
            const out = [];
            const headers = document.querySelectorAll('header.section-header, .section-header');
            for (const h of headers) {
                const h1 = (h.querySelector('h1')?.textContent || '').trim();
                const h2 = (h.querySelector('h2')?.textContent || '').trim();
                // Walk siblings until the next section header
                let next = h.nextElementSibling;
                const links = [];
                while (next) {
                    if (next.classList && next.classList.contains('section-header')) break;
                    const a = next.querySelectorAll('a[href*="/en/model/"]');
                    for (const el of a) {
                        const t = el.textContent.trim();
                        if (t) links.push({text: t, href: el.getAttribute('href')});
                    }
                    next = next.nextElementSibling;
                }
                out.push({header: h1, sub: h2, links: links});
            }
            return out;
        }
    """)
    out = []
    seen_hrefs = set()
    for sec in sections:
        header_lower = sec["header"].lower()
        sub_lower = sec["sub"].lower()
        # Skip non-product sections (news, reviews, etc.)
        if not any(t in header_lower or t in sub_lower
                   for t in ("tv", "television", "monitor", "monitors")):
            continue
        is_tv_section = "tv" in header_lower or "television" in header_lower or "tvs" in header_lower
        is_monitor_section = "monitor" in header_lower
        if is_tv_section and not include_tv:
            continue
        if not is_tv_section and not is_monitor_section:
            # Could be a section that just says brand name (no category hint). Skip
            # to be safe — we don't want to scrape the wrong thing.
            continue
        for link in sec["links"]:
            href = link["href"]
            if not href or href in seen_hrefs:
                continue
            text = link["text"]
            import re as _re
            m = _re.match(r"^(\d+(?:\.\d+)?)[\"\u2033]\s*(.+?)$", text)
            size = float(m.group(1)) if m else None
            model = m.group(2).strip() if m else None
            seen_hrefs.add(href)
            out.append({"href": href, "size": size, "model": model,
                        "section": sec["header"]})
    return out


# TV-only keywords found in "Features" / "Additional features" fields.
# These are LG/Samsung/Sony TV-platform features that are never present on
# desktop monitors.
_TV_KEYWORDS = (
    "webOS", "ThinQ AI", "ThinQ", "Magic Remote", "Magic Explorer",
    "Filmmaker Mode", "Dolby Vision IQ", "LG Channels", "Sport Alert",
    "AI Concierge", "Multi View", "Room to Room Share", "Always Ready",
    "Wow Orchestra", "AI Picture", "AI Sound Pro", "AI Upscaling",
    "4K Upscaling", "4K AI Upscaling", "HDR10 Pro", "HDR Expression",
    "Apple AirPlay", "Apple HomeKit", "Google Assistant", "Amazon Alexa",
    "Art Gallery", "α9 AI Processor", "α8 AI Processor", "α7 AI Processor",
    "a9 AI Processor", "a8 AI Processor", "a7 AI Processor",
    "Ambient Mode", "Q-Symphony", "OTS (Object Tracking Sound)",
    "Smart Calibration", "EyeComfort", "Samba TV", "Live Translate",
    "Multi View with 2 screens", "Wow Interface", "Smart TV",
)


def is_tv_model(page: Page, html: str) -> bool:
    """Detect if a model page is a TV by examining its spec table.

    Heuristic: a model is a TV if any of these is true
    (whichever fires first):
      1) Features / Additional features contain a TV-only keyword
         (webOS, ThinQ AI, Magic Remote, Filmmaker Mode, ...).
      2) ALL three ergonomic adjustments are "No": height adjustment,
         pivot, swivel. TVs almost universally ship with all three as "No";
         monitors always have at least one.
      3) Size is present and > 49" (very large sizes are almost always
         TVs — desktop monitors max out around 49" UltraWide).

    Returns True if the model should be SKIPPED as a TV.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.model-information-table tr")
    fields = {}
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        label, _desc = _extract_label_text(tds[0])
        if not label:
            continue
        value = tds[1].get_text(" ", strip=True)
        fields[label] = value

    # Check 1: TV keywords
    haystack = (fields.get("Features", "") + " " + fields.get("Additional features", "")).lower()
    for kw in _TV_KEYWORDS:
        if kw.lower() in haystack:
            return True

    # Check 2: missing/no-ergonomics + at least one indicator
    # TVs are almost always missing height adjustment AND pivot AND swivel.
    # Some TVs do support tilt (pedestal stand), so we don't require tilt=No.
    # Require at least 2 of those 3 to be present and all "No".
    ergo_keys = ("Height adjustment", "Landscape/portrait pivot", "Left/right swivel")
    ergo_values = [fields.get(k, "").strip().lower() for k in ergo_keys]
    present = [v for v in ergo_values if v]
    if len(present) >= 2 and all(v == "no" for v in present):
        # If the brand-page link already told us this is a small size (< 27"),
        # the model is almost certainly a budget office monitor, not a TV.
        # But we don't have that here — defer to the keyword check.
        # For larger sizes (>= 27"), all three = No is a strong TV signal.
        size = _parse_size_inches(fields.get("Size class", ""))
        if size and size >= 27:
            return True

    return False


# TV-only keywords found in "Features" / "Additional features" fields.
# These are LG/Samsung/Sony TV-platform features that are never present on
# desktop monitors.
_TV_KEYWORDS = (
    "webOS", "ThinQ AI", "ThinQ", "Magic Remote", "Magic Explorer",
    "Filmmaker Mode", "Dolby Vision IQ", "LG Channels", "Sport Alert",
    "AI Concierge", "Multi View", "Room to Room Share", "Always Ready",
    "Wow Orchestra", "AI Picture", "AI Sound Pro", "AI Upscaling",
    "4K Upscaling", "4K AI Upscaling", "HDR10 Pro", "HDR Expression",
    "Apple AirPlay", "Apple HomeKit", "Google Assistant", "Amazon Alexa",
    "Art Gallery", "α9 AI Processor", "α8 AI Processor", "α7 AI Processor",
    "a9 AI Processor", "a8 AI Processor", "a7 AI Processor",
    "Ambient Mode", "Q-Symphony", "OTS (Object Tracking Sound)",
    "Smart Calibration", "EyeComfort", "Samba TV", "Live Translate",
    "Multi View with 2 screens", "Wow Interface", "Smart TV",
)


def is_tv_model(page: Page, html: str) -> bool:
    """Detect if a model page is a TV by examining its spec table.

    Heuristic: a model is a TV if any of these is true
    (whichever fires first):
      1) Features / Additional features contain a TV-only keyword
         (webOS, ThinQ AI, Magic Remote, Filmmaker Mode, ...).
      2) ALL four ergonomic adjustments are "No": height adjustment,
         tilt, swivel/forward-backward, pivot. TVs almost universally
         ship with all four as "No"; monitors always have at least one.
      3) Size is present and > 49" (very large sizes are almost always
         TVs — desktop monitors max out around 49" UltraWide).

    Returns True if the model should be SKIPPED as a TV.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.model-information-table tr")
    fields = {}
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        label, _desc = _extract_label_text(tds[0])
        if not label:
            continue
        # Stash the raw value text
        value = tds[1].get_text(" ", strip=True)
        fields[label] = value

    # Check 1: TV keywords
    haystack = (fields.get("Features", "") + " " + fields.get("Additional features", "")).lower()
    for kw in _TV_KEYWORDS:
        if kw.lower() in haystack:
            return True

    # Check 2: missing/no-ergonomics + at least one indicator
    # TVs are almost always missing height adjustment AND pivot AND swivel.
    # Some TVs do support tilt (pedestal stand), so we don't require tilt=No.
    # Require at least 3 of those 3 to be present and all "No".
    ergo_keys = ("Height adjustment", "Landscape/portrait pivot", "Left/right swivel")
    ergo_values = [fields.get(k, "").strip().lower() for k in ergo_keys]
    present = [v for v in ergo_values if v]
    if len(present) >= 2 and all(v == "no" for v in present):
        # If the brand-page link already told us this is a small size (< 27"),
        # the model is almost certainly a budget office monitor, not a TV.
        # But we don't have that here — defer to the keyword check.
        # For larger sizes (>= 27"), all three = No is a strong TV signal.
        size = _parse_size_inches(fields.get("Size class", ""))
        if size and size >= 27:
            return True

    return False


def scrape_model(context: BrowserContext, page: Page, model_url: str, brand_url: str,
                 also_check_tv: bool = False) -> dict:
    """Scrape a single model page. Returns parsed dict.

    If also_check_tv is True, the returned dict will also include
    "_is_tv": True/False and "_tv_reason": "<keyword>"/"<ergonomics>".
    """
    page.goto(model_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    if "verify you are human" in page.content().lower():
        if not bypass_antibot(context, page):
            return {"source_url": model_url, "source_id": model_url.rstrip("/").split("/")[-1],
                    "brand_url": brand_url, "scrape_status": "failed",
                    "scrape_error": "antibot bypass failed"}
    html = page.content()
    data = parse_model_page(html, model_url, brand_url)
    if also_check_tv:
        if is_tv_model(page, html):
            data["_is_tv"] = True
        else:
            data["_is_tv"] = False
    return data


def run(brand_urls: list[str], db: dict, rate_limit: float = 2.0,
        only_models: Optional[list[str]] = None, dry_run: bool = False,
        max_models: Optional[int] = None,
        max_size: Optional[float] = None, skip_tv: bool = False,
        include_tv: bool = False):
    """Scrape one or more brands end-to-end.

    Filters:
    - skip_tv / include_tv: section-header based TV/monitor split (default:
      monitor only). The brand page groups models under "Desktop monitors"
      and "TVs" section headers; we honor those.
    - max_size: skip models whose size_inches > this value.
    """
    if skip_tv and max_size is None:
        max_size = 49.0  # desktop monitors max out around 49" UltraWide

    conn = psycopg2.connect(**db)
    inserted = 0
    failed = 0
    skipped_tv = 0
    skipped_size = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 1100},
            user_agent=UA,
        )
        ctx.add_init_script(ANTI_BOT_INIT)
        load_saved_cookies(ctx)
        page = ctx.new_page()

        for brand_url in brand_urls:
            print(f"\n[brand] {brand_url}")
            # Handle direct model URLs
            if "/en/model/" in brand_url:
                # Direct model URL — treat as a single model with no parsed size
                model_entries = [{"href": brand_url, "size": None, "model": None,
                                  "section": ""}]
            else:
                # Visit brand page; collect model links (filtered by section header)
                page.goto(brand_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
                if "verify you are human" in page.content().lower():
                    bypass_antibot(ctx, page)
                    page.goto(brand_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)
                model_entries = get_brand_page_model_links(page, brand_url,
                                                          include_tv=include_tv)
                # Stats
                section_counts = {}
                for m in model_entries:
                    section_counts[m["section"]] = section_counts.get(m["section"], 0) + 1
                for sec, n in section_counts.items():
                    print(f"    {sec}: {n} models")
                print(f"  Found {len(model_entries)} model links "
                      f"({len(section_counts)} sections)")

            if only_models:
                model_entries = [m for m in model_entries
                                 if any(only in (m["href"] or "") for only in only_models)]
            if max_size is not None:
                before = len(model_entries)
                model_entries = [m for m in model_entries
                                 if m["size"] is None or m["size"] <= max_size]
                skipped_size += before - len(model_entries)
            if max_models:
                model_entries = model_entries[:max_models]

            for entry in model_entries:
                model_url = entry["href"]
                if entry["size"] is not None:
                    sec_short = entry["section"].split(" - ")[-1] if entry["section"] else ""
                    print(f"  [model {entry['size']}\" / {sec_short:<10}] {entry['model']} -> {model_url}")
                else:
                    print(f"  [model] {model_url}")
                data = scrape_model(ctx, page, model_url, brand_url,
                                    also_check_tv=skip_tv)
                if skip_tv and data.get("_is_tv"):
                    print(f"    [skip] detected as TV")
                    skipped_tv += 1
                    continue
                if dry_run:
                    print(f"    [dry-run] {data.get('brand')} {data.get('model')} - "
                          f"{data.get('size_inches')}\" {data.get('resolution')} "
                          f"{data.get('nits')} nits ({data.get('scrape_status')})")
                else:
                    ok = upsert_model(conn, data)
                    if ok:
                        print(f"    [ok] {data.get('brand')} {data.get('model')} - "
                              f"{data.get('size_inches')}\" {data.get('resolution')} "
                              f"{data.get('nits')} nits")
                        inserted += 1
                    else:
                        failed += 1
                time.sleep(rate_limit)

        browser.close()
    conn.close()
    print(f"\n[done] {inserted} inserted, {failed} failed, "
          f"{skipped_size} skipped (size>{max_size}), {skipped_tv} skipped (TV) "
          f"(dry_run={dry_run})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand-url", help="Single brand URL (e.g. https://www.displayspecifications.com/en/brand/505a43)")
    ap.add_argument("--brand-list", help="File with one brand URL per line")
    ap.add_argument("--model-url", help="Single model URL (skip brand discovery)")
    ap.add_argument("--only", help="Comma-separated substrings to filter models")
    ap.add_argument("--max", type=int, help="Max models per brand")
    ap.add_argument("--max-size", type=float, help="Skip models with size > N inches (default 49 if --skip-tv)")
    ap.add_argument("--skip-tv", action="store_true",
                    help="Skip TV models. The brand page groups models under "
                         "'Desktop monitors' and 'TVs' section headers — we honor those.")
    ap.add_argument("--include-tv", action="store_true",
                    help="Also scrape TV sections (off by default)")
    ap.add_argument("--rate", type=float, default=2.0, help="Seconds between requests")
    ap.add_argument("--dry-run", action="store_true", help="Parse but don't write to DB")
    ap.add_argument("--db-url", help="Override DB connection (e.g. postgresql://user:pass@host:port/db)")
    args = ap.parse_args()

    db = DEFAULT_DB
    if args.db_url:
        from urllib.parse import urlparse
        u = urlparse(args.db_url)
        db = dict(host=u.hostname, port=u.port or 5432, dbname=u.path.lstrip("/"),
                  user=u.username, password=u.password)

    brand_urls = []
    if args.brand_url:
        brand_urls.append(args.brand_url)
    if args.brand_list:
        with open(args.brand_list, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    brand_urls.append(line)
    if args.model_url:
        brand_urls.append(args.model_url)
    if not brand_urls:
        ap.error("Provide --brand-url, --brand-list, or --model-url")
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    run(brand_urls, db, rate_limit=args.rate, only_models=only,
        dry_run=args.dry_run, max_models=args.max,
        max_size=args.max_size, skip_tv=args.skip_tv,
        include_tv=args.include_tv)


if __name__ == "__main__":
    main()
