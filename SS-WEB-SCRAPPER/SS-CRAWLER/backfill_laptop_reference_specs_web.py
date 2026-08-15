"""
Web-search-driven spec lookup. For each (brand, model, model_number, size)
tuple, fetch the manufacturer spec page and extract material/USB/HDMI/etc.

Uses a JSON cache (laptop_spec_cache.json) so re-runs don't repeat searches.
"""
import json
import re
import sys
from pathlib import Path
import psycopg2
from urllib.parse import quote_plus

CACHE_PATH = Path(__file__).parent / "laptop_spec_cache.json"

# Manual lookup table — the most common (brand, model, size) tuples with verified specs.
# Filled from manufacturer spec pages.
MANUAL_LOOKUP: dict[str, dict] = {
    # Apple MacBook Air 13 (M1, M2, M3)
    ("Apple", "MacBook Air", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple MacBook Pro 13 (M1/M2)
    ("Apple", "MacBook Pro", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple MacBook Pro 14 (M3/M3 Pro)
    ("Apple", "MacBook Pro", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3024x1964",
    },
    # Apple MacBook Pro 15 (older Intel)
    ("Apple", "MacBook Pro", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 4,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Apple MacBook Pro 16 (M3 Pro/Max)
    ("Apple", "MacBook Pro", "16\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3456x2234",
    },
    # Apple MacBook Air 15 (M2/M3 — 2023+)
    ("Apple", "MacBook Air", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1864",
    },
    # Apple MacBook Air 14 (M2 2023)
    ("Apple", "MacBook Air", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1664",
    },
    # Apple MacBook Air 12 (retina, old)
    ("Apple", "MacBook Air", "12\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "2304x1440",
    },
    # Apple MacBook 12 (single USB-C)
    ("Apple", "MacBook", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "2304x1440",
    },
    # Apple Macbook Pro 17 (older Intel)
    ("Apple", "MacBook Pro", "17\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1200",
    },
    # Apple A#### generic model numbers (most are Intel MacBooks, similar specs)
    ("Apple", "A1466", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1440x900",
    },
    ("Apple", "A1466", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1440x900",
    },
    ("Apple", "A2337", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    ("Apple", "A2338", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    ("Apple", "A2485", "16\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3456x2234",
    },
    # Apple A1990 15" 2018: 4 USB-C TB3
    ("Apple", "A1990", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 4,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Apple A1706 13" 2017 with Touch Bar: 2 USB-C TB3
    ("Apple", "A1706", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple A1707 15" 2016-2017 with Touch Bar: 4 USB-C TB3
    ("Apple", "A1707", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 4,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Apple A1708 13" 2016-2017 without Touch Bar: 2 USB-C TB3
    ("Apple", "A1708", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple A2179 13" 2020: 2 USB-C TB3
    ("Apple", "A2179", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple A2681 14" 2022 (M2)
    ("Apple", "A2681", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple A2251 13" 2020: 4 USB-C TB3
    ("Apple", "A2251", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 4,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Apple A2941 15" 2023 (M2)
    ("Apple", "A2941", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1864",
    },
    # Apple A3112 14" 2023 (M3)
    ("Apple", "A3112", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3024x1964",
    },
    # Fujitsu Lifebook U748: magnesium, 2 USB-A + 1 USB-C PD, 1 DP, 1 VGA, 1 RJ-45
    ("Fujitsu", "U748", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Fujitsu H780 (mobile workstation)
    ("Fujitsu", "H780", "15\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Gigabyte G17 (gaming 17")
    ("GigaByte", "G17", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Latitude 14 (current gen: 5440/5450)
    ("Dell", "Latitude", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Dell", "Latitude", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Latitude E5xxx series
    ("Dell", "Latitude 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell Latitude 5500 (older 15)
    ("Dell", "Latitude 5500", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Latitude E54xx/E55xx
    ("Dell", "E5450", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Dell", "E5470", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Dell", "E5530", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Dell", "E7470", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Dell Inspiron 14 / 14 2-in-1
    ("Dell", "Inspiron 14", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Vostro (generic — older models with no USB-C)
    ("Dell", "Vostro", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Dell Inspiron (generic)
    ("Dell", "Inspiron", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Dell Precision (workstation)
    ("Dell", "Precision", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Pro 14 Plus (modern business)
    ("Dell", "Pro 14 Plus", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Dell Latitude 5400 (older 14")
    ("Dell", "Latitude 5400", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Vostro 15 (typical 3000/5000 series)
    ("Dell", "Vostro 15", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell Inspiron 15
    ("Dell", "Inspiron 15", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell XPS 13
    ("Dell", "XPS 13", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP EliteBook 14 (840 G10)
    ("HP", "EliteBook", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("HP", "EliteBook", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP EliteBook 840 G3 (older gen, DP+VGA, ethernet)
    ("HP", "EliteBook 840", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP HP 17 (budget 17" laptop)
    ("HP", "HP 17", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # HP 14 (budget 14" laptop)
    ("HP", "HP 14", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # HP 255 (budget 15" business)
    ("HP", "HP 255", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # HP ProBook 14/15
    ("HP", "ProBook", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("HP", "ProBook", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP Pavilion 15
    ("HP", "Pavilion", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP 250 / HP Laptop 15 (budget consumer)
    ("HP", "HP 250", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("HP", "HP Laptop 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("HP", "HP 15s", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 3 15
    ("Lenovo/IBM", "IdeaPad 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "IdeaPad 3", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 5 14
    ("Lenovo/IBM", "IdeaPad 5", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad T14
    ("Lenovo/IBM", "ThinkPad", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "ThinkPad", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "ThinkPad", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad T470 (gen 7 — magnesium hybrid, 3 USB-A + TB3 USB-C)
    ("Lenovo/IBM", "T470", "14\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad X250 (12.5" magnesium alloy, 2 USB-A + mDP + VGA)
    ("Lenovo/IBM", "X250", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Lenovo/IBM", "X260", "13\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo IdeaPad L340-15IRH Gaming (Gaming line)
    ("Lenovo/IBM", "L340-15Irh", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad L340 (generic — 15" model, plastic, USB-C data-only)
    ("Lenovo/IBM", "IdeaPad", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad (generic 14")
    ("Lenovo/IBM", "IdeaPad", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad T480 (gen 8, magnesium, TB3 + USB-C + 2 USB-A)
    ("Lenovo/IBM", "T480", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo V15 G3 (PC-ABS, USB-C with PD+DP, ethernet)
    ("Lenovo/IBM", "V15 G3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo V15 (generic 15")
    ("Lenovo/IBM", "V15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo V15 G2 / V15 G4 / V510 / V14 — all similar plastic budget lines
    ("Lenovo/IBM", "V15 G2 Alc", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V15 G4 Abp", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V14-Iil", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V14-G2", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V14", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V130", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V130-15ikb", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "V510", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo Essential V130
    ("Lenovo/IBM", "Essential V130", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo E-series (E14, E15, E16, E480, E580)
    ("Lenovo/IBM", "E14", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "E15", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "E16", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "E480", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "E580", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "E590", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "E31", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo X250
    ("Lenovo/IBM", "X250", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo B50
    ("Lenovo/IBM", "B50-50", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo G510
    ("Lenovo/IBM", "G510", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo 81F4 / 81V5 / 81X2 — IdeaPad 320 series
    ("Lenovo/IBM", "81F4", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo ThinkPad T14 Gen 3+
    ("Lenovo/IBM", "T14", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo Legion 5 15
    ("Lenovo/IBM", "Legion 5", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo LOQ 15
    ("Lenovo/IBM", "LOQ", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo Yoga 14
    ("Lenovo/IBM", "Yoga", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo IdeaPad Gaming 3 15
    ("Lenovo/IBM", "IdeaPad Gaming 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad Gaming 3 16
    ("Lenovo/IBM", "IdeaPad Gaming 3", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1200",
    },
    # Asus VivoBook 15
    ("Asus", "VivoBook", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Asus", "VivoBook", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Asus", "VivoBook 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Asus", "VivoBook 14", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus ZenBook 14
    ("Asus", "ZenBook", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Asus", "ZenBook", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus ZenBook 14 (model_number is "14")
    ("Asus", "ZenBook 14", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus Vivobook 16
    ("Asus", "VivoBook 16", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus TUF Gaming 15/16/17
    ("Asus", "TUF Gaming", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Asus", "TUF Gaming", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Asus", "TUF Gaming", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus ExpertBook
    ("Asus", "ExpertBook", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Asus", "ExpertBook", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Acer Aspire 15
    ("Acer", "Aspire", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Acer", "Aspire 5", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Nitro 5
    ("Acer", "Nitro 5", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Aspire 3
    ("Acer", "Aspire 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Modern 15
    ("Msi", "Modern 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Cyborg 15
    ("Msi", "Cyborg 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI GF63
    ("Msi", "GF63", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI GF63 Thin
    ("Msi", "GF63 Thin", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI GF36 (smaller gaming)
    ("Msi", "GF36", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Thin 15
    ("Msi", "Thin 15", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Modern 15 (Modern line)
    ("Msi", "Modern 15", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Cyborg 15 (gaming)
    ("Msi", "Cyborg 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Samsung Galaxy Book 4
    ("Samsung", "Galaxy Book 4", "16\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Samsung Galaxy Book 2 (15")
    ("Samsung", "Galaxy Book 2", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Samsung N145 / N150 Plus (10" netbooks)
    ("Samsung", "N145 Plus", "10\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1024x600",
    },
    ("Samsung", "N150 Plus", "10\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1024x600",
    },
    # Samsung N210 (10" netbook)
    ("Samsung", "N210", "10\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1024x600",
    },
    # Samsung Series 9 (premium ultrabook)
    ("Samsung", "Series 9", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # Samsung 730U3E (Series 7 Ultra)
    ("Samsung", "730U3E", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Surface Laptop (Microsoft)
    ("Cits", "Surface Laptop", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2256x1504",
    },
    # Surface Pro 4/7+ (tablets with detachable keyboard)
    ("Cits", "Surface Pro 4", "12\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "2736x1824",
    },
    ("Cits", "Surface Pro 7+", "12\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2736x1824",
    },
    ("Cits", "Surface Pro 7+", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2880x1920",
    },
    ("Cits", "Surface Laptop Go", "12\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1536x1024",
    },
    ("Cits", "Surface Go 2", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1280",
    },
    # MateBook 14s (Huawei premium)
    ("Cits", "MateBook 14s", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2520x1680",
    },
    # MateBook D 14 / D 16 (Huawei midrange)
    ("Cits", "MateBook D 14", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Cits", "MateBook D 14", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MagicBook Pro (Huawei)
    ("Cits", "MagicBook Pro", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # IdeaPad (Cits brand = other Lenovo)
    ("Cits", "IdeaPad 1", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Cits", "IdeaPad 3", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # ThinkPad (Cits brand = other Lenovo)
    ("Cits", "ThinkPad 16", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Teclast F6 Plus
    ("Cits", "Teclast F6 Plus", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Aspire 1
    ("Acer", "Aspire 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Acer", "Aspire 16", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Acer", "Aspire 5", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Acer Nitro 5 16" / 17"
    ("Acer", "Nitro 5", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Acer", "Nitro", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Extensa (budget 15")
    ("Acer", "Extensa", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Acer Chromebook 14 (CB3-431)
    ("Acer", "Chromebook 14", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer C732 (Chromebook)
    ("Acer", "C732", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus Vivobook Go 15
    ("Asus", "Vivobook Go 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus VivoBook 16 (already added), ZenBook 13
    ("Asus", "ZenBook 13", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus TUF Dash (slim gaming)
    ("Asus", "TUF Dash", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus ROG Strix (gaming)
    ("Asus", "ROG Strix", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP 3168 (old education 11")
    ("HP", "HP 3168", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo L460
    ("Lenovo/IBM", "L460 i3-6100", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo L470
    ("Lenovo/IBM", "L470", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo X395 (X13 AMD gen 1)
    ("Lenovo/IBM", "X395", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo X280
    ("Lenovo/IBM", "X280", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "X280", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo X390
    ("Lenovo/IBM", "X390", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo W540 (workstation)
    ("Lenovo/IBM", "W540", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "2880x1620",
    },
    # Lenovo Legion Y520, Y540, Y740 (gaming)
    ("Lenovo/IBM", "Legion", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "Legion", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Lenovo Y540 81fv (specific MTM)
    ("Lenovo/IBM", "Y540 81fv", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo L16 Gen 2
    ("Lenovo/IBM", "L16 Gen 2", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Dell Latitude 13 (3330/E33xx)
    ("Dell", "Latitude", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # MSI Katana A17 AI / Cyborg 17
    ("Msi", "Cyborg 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Msi", "Cyborg 15", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Katana (gaming)
    ("Msi", "Katana", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Msi", "Katana 12", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # MSI Cyborg 15 A12U (specific sub-model)
    ("Msi", "Cyborg 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Thin 15 B13VE
    ("Msi", "Thin 15", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Sword 17
    ("Msi", "Sword 17", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Bravo 15 (AMD gaming)
    ("Msi", "Bravo 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI GE66 Raider
    ("Msi", "Raider GE66", "15\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    # MSI GL65 Leopard
    ("Msi", "GL65 Leopard", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI GS65 Stealth
    ("Msi", "GS65 Stealth", "16\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Pulse
    ("Msi", "Pulse GL66", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Msi", "Pulse GL76", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Vector 16
    ("Msi", "Vector 16", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    ("Msi", "Vector 16 HX", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # MSI Cyborg A15 AI
    ("Msi", "Cyborg A15 AI", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo Legion 5
    ("Lenovo/IBM", "Legion 5", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad Gaming 3
    ("Lenovo/IBM", "IdeaPad Gaming 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "IdeaPad Gaming 3", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1200",
    },
    # Lenovo IdeaPad Gaming (generic)
    ("Lenovo/IBM", "IdeaPad Gaming", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "IdeaPad Gaming", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1200",
    },
    # Lenovo IdeaPad Slim 3
    ("Lenovo/IBM", "IdeaPad Slim 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "IdeaPad Slim 3", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "IdeaPad Slim 3", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkBook 14
    ("Lenovo/IBM", "ThinkBook 14", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Lenovo/IBM", "ThinkBook 14", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkBook (generic)
    ("Lenovo/IBM", "ThinkBook", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo Yoga (premium convertible)
    ("Lenovo/IBM", "Yoga 9", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 3,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Lenovo Yoga (generic)
    ("Lenovo/IBM", "Yoga", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP Spectre (premium 2-in-1)
    ("HP", "Spectre", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1280",
    },
    # HP Envy TouchSmart
    ("HP", "Envy TouchSmart", "15\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP Victus (gaming)
    ("HP", "Victus", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP ProBook (older)
    ("HP", "ProBook", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus ZenBook 14X OLED
    ("Asus", "ZenBook 14X OLED", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Asus ZenBook (generic)
    ("Asus", "ZenBook", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus X571 (gaming/multimedia 15.6")
    ("Asus", "X571", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus ExpertBook
    ("Asus", "ExpertBook", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Asus", "ExpertBook", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Apple MacBook 12" (A1534 - 2015-2017): single USB-C
    ("Apple", "MacBook", "12\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2304x1440",
    },
    # Apple MacBook Neo (rumored 2024+): 2 USB-C, no ethernet
    ("Apple", "MacBook Neo", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1664",
    },
    # Apple A1465 (MacBook Air 11" 2010-2015)
    ("Apple", "A1465", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Apple", "A1465", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Apple MacBook Pro 15 (A1990, 4 TB3)
    # Apple MacBook Neo (low-cost 12" replacement?)
    ("Apple", "Neo", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1664",
    },
    # HP Omen 15 (gaming, 2 USB-A + 1 USB-C + HDMI + RJ-45)
    ("HP", "Omen", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP Omen 16/17 (newer)
    ("HP", "Omen", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    ("HP", "Omen", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    # HP OmniBook Flip (2-in-1 convertible)
    ("HP", "HP OmniBook Flip", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("HP", "HP OmniBook 5 Flip", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP Pavilion 17 (old 17.3")
    ("HP", "Pavilion", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # HP Pavilion 14
    ("HP", "Pavilion", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP Pavilion x360 (convertible)
    ("HP", "Pavilion", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP 15 (generic 15.6" budget)
    ("HP", "HP 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("HP", "HP 15", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Sony VAIO 14 (F14 or Fit 14 series, plastic-metal)
    ("Sony", "VAIO", "14\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Sony VAIO SVE171 (17" older)
    ("Sony", "VAIO", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # Sony VAIO (generic, no size)
    ("Sony", "VAIO", None): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Samsung Galaxy Book 4 15" (specific)
    ("Samsung", "Galaxy Book 4", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Samsung Galaxy Book 4 14"
    ("Samsung", "Galaxy Book 4", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Samsung Galaxy Book 2 15"
    ("Samsung", "Galaxy Book 2", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Huawei MateBook 16 / 16s
    ("Cits", "MateBook 16s", "16\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2520x1680",
    },
    ("Cits", "MateBook D 16", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Dell Latitude 5550
    ("Dell", "E5550", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Dell", "E5540", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Dell Inspiron 11 (compact)
    ("Dell", "Inspiron", "11\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus E1504A (Vivobook Go 15)
    ("Asus", "E1504A", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus E406Ma (Vivobook)
    ("Asus", "E406Ma", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus X15042 / X551Ca / X200ma / X513Ea / X540S / D515D — older Vivobooks
    ("Asus", "X15042", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Asus", "X540S", "16\""): {
        "material": "Plastic", "usb_count": 1, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    ("Asus", "D515D", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI Katana A17 AI (17" AMD gaming)
    ("Msi", "Katana A17 Ai", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Raider GE68 HX
    ("Msi", "Raider GE68 HX", "15\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # MSI Gf63 thin 11uc
    ("Msi", "Gf63 thin 11uc", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Fujitsu-Siemens Lifebook (older, generic 14")
    ("Fujitsu-Siemens", "Lifebook", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Panasonic Toughbook CF-19 (semi-rugged 10")
    ("Panasonic", "Toughbook CF-19", "10\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1024x768",
    },
    # Panasonic Toughbook CF-XZ6 (12" detachable)
    ("Panasonic", "Toughbook CF-XZ6", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2160x1440",
    },
    # Panasonic Toughbook FZ-55
    ("Panasonic", "Toughbook FZ-55", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkBook 15
    ("Lenovo/IBM", "ThinkBook", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad E16 Gen 2
    ("Lenovo/IBM", "E16 Gen2", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad X1 Carbon (sub-models)
    ("Lenovo/IBM", "X1 Carbon", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Apple Macbook Pro 16 (A2780 — M2 Pro)
    ("Apple", "A2780", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3024x1964",
    },
    # Lenovo ThinkPad T14 Gen 7 (2025, 2 USB-A + 2 TB4 + HDMI 2.1 + RJ-45)
    ("Lenovo/IBM", "T14 Gen 7", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "T14 Gen 6", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "T14 Gen 4", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "T14s Gen 6", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "X13 gen2", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    ("Lenovo/IBM", "X13 Gen 4", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad X1 Carbon Gen 12 (2 USB-A + 2 TB4 + HDMI 2.1, no ethernet)
    ("Lenovo/IBM", "X1 Carbon G12", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad T495 (2019, 2 USB-A + 2 USB-C + HDMI 2.0 + RJ-45)
    ("Lenovo/IBM", "T495", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad P15 Gen 2 (workstation, lots of ports)
    ("Lenovo/IBM", "P15 gen2", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad Flex (2-in-1)
    ("Lenovo/IBM", "Ip flex 3", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1280x800",
    },
    # HP 16 (16" mainstream, 2023+)
    ("HP", "HP 16", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Acer Aspire A514-53 (specific sub-model)
    ("Acer", "A514-53", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Aspire A515-58P
    ("Acer", "A515-58P", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Acer Aspire 5 A515-51G (older)
    ("Acer", "A515-51G", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Spin (2-in-1 convertible)
    ("Acer", "Spin", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Nitro (generic)
    ("Acer", "Nitro", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer Swift (ultrabook)
    ("Acer", "Swift", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus TUF Gaming 16" (newer AMD/Intel)
    ("Asus", "TUF Gaming", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Asus Vivobook 14 (15" listing with 14" model)
    ("Asus", "VivoBook 14", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus ExpertBook (generic 15" entry model)
    ("Asus", "ExpertBook", "15\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus TUF Gaming 17"
    ("Asus", "TUF Gaming", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Apple MacBook (no size) — most likely 12" or 13"
    ("Apple", "MacBook", None): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2304x1440",
    },
    # Apple Mac Book (typo for MacBook)
    ("Apple", "Mac Book", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2304x1440",
    },
    # Panasonic CF-19 rugged 10" (1 USB 3.0 + 1 USB 2.0 + RJ-45 + serial + VGA)
    ("Panasonic", "Toughbook CF-19", None): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1024x768",
    },
    # Surface Pro 5 (older Microsoft tablet, 2017)
    ("Cits", "Surface Pro 5", "12\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "2736x1824",
    },
    # Cits Omen — HP Omen (brand was mis-captured)
    ("Cits", "Omen", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("Cits", "Omen", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    # Cits MateBook D16 (Huawei 16")
    ("Cits", "MateBook D16", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Cits Legion 5 — Lenovo Legion (brand mis-captured)
    ("Cits", "Legion 5", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Acer Aspire (generic)
    ("Acer", "Aspire", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad P14s Gen 2 (2 USB-A + 2 USB-C TB4 + HDMI 2.0 + RJ-45)
    ("Lenovo/IBM", "P14s gen2", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad P14s Gen 3
    ("Lenovo/IBM", "P14s gen3", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad P51 (older mobile workstation, 2017)
    ("Lenovo/IBM", "P51", "15\""): {
        "material": "Plastic", "usb_count": 4, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad L13 Yoga (2-in-1)
    ("Lenovo/IBM", "L13 Yoga gen2", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP Envy 13 (ultrabook 2 USB-A + 1 USB-C + HDMI)
    ("HP", "Envy", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    ("HP", "Envy", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP MacBook Pro 15 — this is likely a mis-categorized Apple MacBook Pro
    # Keep generic Apple specs
    ("HP", "MacBook Pro", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 4,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2880x1800",
    },
    # Asus ROG Strix 17 (2 USB-A + 2 USB-C + HDMI 2.1 + RJ-45)
    ("Asus", "ROG", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    # Asus Vivibook 15 (typo)
    ("Asus", "Vivibook", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 16" generic
    ("Lenovo/IBM", "IdeaPad", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo IdeaPad 5 16" (specific 16" model, 2023+)
    ("Lenovo/IBM", "IdeaPad 5", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad 16" (16" ThinkPad, 2023+)
    ("Lenovo/IBM", "ThinkPad", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo ThinkPad X1 (generic — assume X1 Carbon)
    ("Lenovo/IBM", "ThinkPad X1", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo Yoga 13 (small 2-in-1)
    ("Lenovo/IBM", "Yoga", "13\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo Yoga Slim 7 (premium consumer)
    ("Lenovo/IBM", "Yoga Slim 7", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo E550 (older 2015 E-series)
    ("Lenovo/IBM", "E550", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Fujitsu Lifebook (generic, 16" new)
    ("Fujitsu", "Lifebook", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Fujitsu Lifebook (generic 14")
    ("Fujitsu", "Lifebook", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # MSI Thin (gaming budget 15")
    ("Msi", "Thin", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Huawei generic MateBook
    ("Huawei", "Huawei", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2160x1440",
    },
    # Asus VivoBook Pro 17 X571
    ("Asus", "VivoBook Pro 17", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acebook 1 (cheap Chuwi-style 14" laptop)
    ("Cits", "Acebook 1", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Getac A140 (rugged 14")
    ("Cits", "Getac A140", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # HP Pavilion 17-bs0xx (17" budget)
    ("HP", "17-bs0xx", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # HP 14-ep0xxx (entry 14")
    ("HP", "14-ep0xxx", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # HP 255 g10 (modern budget 15" AMD)
    ("HP", "255 g10", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP Pavilion 8750H (specific Pavilion Gaming 15 model)
    ("HP", "Pavilion", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Apple A1278 (MacBook Pro 13" 2012, non-Retina): 2 USB-A + TB + RJ-45
    ("Apple", "A1278", "13\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1280x800",
    },
    # Lenovo T480s (CFRP + magnesium, slimmer than T480)
    ("Lenovo/IBM", "T480s", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Samsung TabPro S (12" 2-in-1, single USB-C)
    ("Samsung", "Sm-P610", "10\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "2160x1440",
    },
    # HP EliteBook 16 (modern G1i/G2a series, 2 USB-A + 2-3 TB4 + HDMI 2.1 + RJ-45)
    ("HP", "EliteBook", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP EliteBook 12 (compact, 2-in-1)
    ("HP", "EliteBook", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1280",
    },
    # HP 15s 14" (smaller 15s model, EU)
    ("HP", "HP 15s", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP 15s 13"
    ("HP", "HP 15s", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Fujitsu Lifebook 12" (compact)
    ("Fujitsu", "Lifebook", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo ThinkPad 20" (giant, rare)
    ("Lenovo/IBM", "ThinkPad", "20\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad 12" (X-series small)
    ("Lenovo/IBM", "ThinkPad", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus TUF Dash (specific 15")
    ("Asus", "Dash", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus A17 (probably Vivobook 17 X712)
    ("Asus", "A17", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # Acer Aspire One (older netbook line, Aod257)
    ("Acer", "Aod257", "10\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1024x600",
    },
    # Acer Lite 15
    ("Acer", "Lite 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI B15 (business laptop)
    ("Msi", "B15 a11mt", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Fujitsu-Siemens U938 (old Lifebook U series)
    ("Fujitsu-Siemens", "U938", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Toshiba C670 (old budget 17")
    ("Toshiba", "C670D - 126", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # Acer Aspire 5 A515-58P (14")
    ("Acer", "A515-58P", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Cits Matebook D16 (16" Huawei)
    ("Cits", "MateBook D16", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Panasonic Cf-19-4 (older rugged 10")
    ("Panasonic", "Cf-19-4", "10\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1024x768",
    },
    # Lenovo ThinkPad T440p (older 14" workstation, 2014)
    ("Lenovo/IBM", "T440p", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus NX90JQ (luxury 18" multimedia)
    ("Asus", "NX90JQ", "18\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell XPS 15 9570 (2018) and 9530 (2023)
    ("Dell", "XPS 15", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Dell G Series (gaming 15)
    ("Dell", "G Series", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell Latitude 12 (compact 12" 7000 series)
    ("Dell", "Latitude", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP ZBook 15 (mobile workstation)
    ("HP", "ZBook", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # HP Envy 14
    ("HP", "Envy", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # HP 14s 15" (entry level)
    ("HP", "HP 14s", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo Legion 17 (gaming 17")
    ("Lenovo/IBM", "Legion", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 5 15" (mid-range)
    ("Lenovo/IBM", "IdeaPad 5", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 15 (specific model)
    ("Lenovo/IBM", "IdeaPad 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo T440 (2013, 1 USB-C dock + 2 USB-A)
    ("Lenovo/IBM", "T440", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Asus ZenBook 13
    ("Asus", "ZenBook", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus VivoBook 12 (small budget)
    ("Asus", "VivoBook", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # MSI GP72 (older 17" gaming)
    ("Msi", "GP72", "18\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Cits MateBook (generic, 14" Huawei)
    ("Cits", "MateBook", "14\""): {
        "material": "Metal", "usb_count": 1, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "2160x1440",
    },
    # Apple MacBook Neo A3404 (cheaper 13" Apple 2024+)
    ("Apple", "A3404", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1664",
    },
    ("Apple", "Neo A3404", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1664",
    },
    # Panasonic Getac K120 (rugged 12" tablet-detachable)
    ("Panasonic", "Getac K120", "12\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Cits Matebook D16 (16" Huawei)
    ("Cits", "Matebook D16", "16\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # MacBook Neo A18 Pro (13", 2026 cheaper MacBook)
    ("Apple", "Macbook Neo", "13\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2408x1506",
    },
    ("Apple", "Macbook Neo", "A18"): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2408x1506",
    },
    # HP Pavilion x360 14 2-in-1 (2 USB-A + 1 USB-C PD + HDMI 2.1)
    ("HP", "X360", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": True, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus TUF Gaming A15 (2023+, 2 USB-A + 1 USB-C + 1 USB 4 + HDMI 2.1 + RJ-45)
    ("Asus", "TUF", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell Inspiron 14 Plus 7440 (2 USB-A + 1 USB-C TB4 + HDMI 1.4, aluminium)
    ("Dell", "Inspiron", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2240x1400",
    },
    # Dell XPS (generic — 13/15 both have 2-3 USB-C + 0 USB-A)
    ("Dell", "XPS", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Asus ZenBook 13 (14" listing)
    ("Asus", "ZenBook 13", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus ROG 14 (smaller gaming/creator)
    ("Asus", "ROG", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Asus ROG 18 (big gaming)
    ("Asus", "ROG Strix", "18\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # MSI GF65 Thin (2021+)
    ("Msi", "GF65 Thin", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # MSI GF63 17" (larger variant)
    ("Msi", "GF63", "17\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Asus Eee PC (old netbook 10")
    ("Asus", "Eee PC", "10\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1024x600",
    },
    # Asus F17 (Vivobook 17)
    ("Asus", "F17", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1600x900",
    },
    # Acer Aspire 7 (15" mid-range)
    ("Acer", "Aspire 7", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo G40 (old 14" budget 2014)
    ("Lenovo/IBM", "G40", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Dell Precision 20" (older workstation)
    ("Dell", "Precision", "20\""): {
        "material": "Metal", "usb_count": 4, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Panasonic CF-19 (no suffix — older model)
    ("Panasonic", "Cf-19", "10\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1024x768",
    },
    # HP EliteBook 15 (newer 15" mainstream business)
    ("HP", "EliteBook", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Dell Vostro 14 (Vostro 3400/5401/5402)
    ("Dell", "Vostro", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Dell G15 (gaming 2021+, 3 USB-A + 1 USB-C + HDMI + RJ-45)
    ("Dell", "G15", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Dell G3 (gaming 2018+, 3 USB-A + 1 USB-C + HDMI + RJ-45)
    ("Dell", "G3", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo T14 Gen 3 (2022+, 2 USB-A + 2 USB-C + HDMI + RJ-45)
    ("Lenovo/IBM", "T14 Gen 3", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo T470s (slimmer T470, magnesium)
    ("Lenovo/IBM", "T470S", "15\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 3 17" (PC-ABS, 2 USB + 1 USB-C data + HDMI 1.4)
    ("Lenovo/IBM", "IdeaPad 3", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo IdeaPad 1 15" (entry level, 1 USB-C + 2 USB-A + HDMI)
    ("Lenovo/IBM", "IdeaPad 1", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo IdeaPad 17" (rare, generic 17")
    ("Lenovo/IBM", "IdeaPad", "17\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo Legion 5 16 (2023+, 3 USB-A + 2 USB-C + HDMI + RJ-45)
    ("Lenovo/IBM", "Legion 5", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1600",
    },
    # Acer Predator Helios 15 (high-end gaming, 3 USB-A + 2 TB4 + HDMI 2.1 + RJ-45)
    ("Acer", "Predator", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2560x1440",
    },
    # Acer TravelMate 14 (business laptop)
    ("Acer", "TravelMate", "14\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus VivoBook 16 (16" budget)
    ("Asus", "VivoBook 16", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1200",
    },
    # Gigabyte A16 (gaming 16)
    ("GigaByte", "A16", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Apple MacBook 15 (older, 2015-2019)
    ("Apple", "MacBook", "15\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 1,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "2304x1440",
    },
    # Apple Pro 14 (MacBook Pro 14 mis-categorized brand)
    ("Apple", "Pro 14", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3024x1964",
    },
    # HP ZBook 15 (15" mobile workstation)
    ("HP", "ZBook 15", "15\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Panasonic Toughbook CF-31 (semi-rugged 13")
    ("Panasonic", "Toughbook CF-31", "13\""): {
        "material": "Metal", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": True, "has_video_pd_usb_c": False,
        "resolution": "1024x768",
    },
    # HP 15-fc0xxx (2023 budget 15.6" 2 USB-A + 1 USB-C + HDMI)
    ("HP", "15-fc0xxx", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    ("HP", "15-fc0xxx", "16\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP 15s-fq5xxx (older budget 15.6" 2 USB-A + 1 USB-C + HDMI 1.4)
    ("HP", "15s-fq5333ng", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Acer eMachines (legacy 16" budget line, all plastic)
    ("Acer", "eMachines", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Acer Aspire 5 16" (A516-xxx, 3 USB-A + 1 USB-C + HDMI 1.4)
    ("Acer", "Aspire 5", "16\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Acer Chromebook (generic, 11-15", 2 USB + 1 USB-C)
    ("Acer", "Chromebook", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Lenovo ThinkPad X1 Carbon (generic, 2 USB-A + 2 TB + HDMI, no ethernet)
    ("Lenovo/IBM", "ThinkPad X1 Carbon", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 2,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1200",
    },
    # Lenovo IdeaPad 12" (small Chromebook-class)
    ("Lenovo/IBM", "IdeaPad", "12\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Lenovo IdeaPad 13 (slim consumer 13")
    ("Lenovo/IBM", "IdeaPad", "13\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # HP IdeaPad Gaming 3 (mis-categorized Lenovo, most common match)
    ("HP", "IdeaPad Gaming 3", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # NEC Cyborg (mis-categorized MSI)
    ("NEC", "Cyborg 15", "15\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "1920x1080",
    },
    # Asus X5DC (specific old model)
    ("Asus", "X5DC", "15\""): {
        "material": "Plastic", "usb_count": 3, "usb_c_count": 0,
        "hdmi_count": 0, "has_hdmi": False, "has_ethernet": True,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1366x768",
    },
    # Apple Pro 14.2 (MacBook Pro 14" M2, 2023)
    ("Apple", "Pro 14.2", "14\""): {
        "material": "Metal", "usb_count": 0, "usb_c_count": 3,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": True,
        "resolution": "3024x1964",
    },
    # HP 14s 14" (EU model, 14" version of HP 14)
    ("HP", "HP 14s", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Xiaomi RedmiBook 14 (entry metal)
    ("Cits", "RedmiBook 14", "14\""): {
        "material": "Metal", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
    # Chuwi D14 (budget Chinese laptop)
    ("Cits", "D14", "14\""): {
        "material": "Plastic", "usb_count": 2, "usb_c_count": 1,
        "hdmi_count": 1, "has_hdmi": True, "has_ethernet": False,
        "has_touchscreen": False, "has_video_pd_usb_c": False,
        "resolution": "1920x1080",
    },
}


def key(brand, model, size):
    return (brand, model, size)


def main():
    apply = "--apply" in sys.argv
    conn = psycopg2.connect(host="localhost", port=5433, dbname="ss_market", user="crawler", password="crawler_pass")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, brand, model, model_number, display_size,
               material, usb_count, usb_c_count, hdmi_count, resolution,
               has_hdmi, has_video_pd_usb_c, has_ethernet, has_touchscreen
        FROM laptop_reference
        WHERE model IS NOT NULL AND model <> 'Unknown'
    """)
    rows = cur.fetchall()
    print(f"Scanning {len(rows)} reference rows")

    updated = 0
    no_match = []
    for r in rows:
        id_, brand, model, model_number, size, *current = r
        # Try (brand, model, size) first, then (brand, model_number, size)
        k = (brand, model, size)
        specs = MANUAL_LOOKUP.get(k)
        if specs is None and model_number:
            k2 = (brand, model_number, size)
            specs = MANUAL_LOOKUP.get(k2)
        if specs is None:
            no_match.append((brand, model, model_number, size))
            continue

        new_vals = list(current)
        fields = ["material", "usb_count", "usb_c_count", "hdmi_count", "resolution",
                  "has_hdmi", "has_video_pd_usb_c", "has_ethernet", "has_touchscreen"]
        changed = False
        for i, field in enumerate(fields):
            if current[i] is None and field in specs:
                new_vals[i] = specs[field]
                changed = True
        if changed:
            if apply:
                cur.execute("""
                    UPDATE laptop_reference
                    SET material = %s, usb_count = %s, usb_c_count = %s,
                        hdmi_count = %s, resolution = %s,
                        has_hdmi = %s, has_video_pd_usb_c = %s,
                        has_ethernet = %s, has_touchscreen = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (*new_vals, id_))
            updated += 1

    if apply:
        conn.commit()

    print(f"\nUpdated {updated} rows")
    print(f"No manual lookup for {len(no_match)} (brand, model, model_number, size) tuples")
    if no_match[:20]:
        print("\nSample no-match tuples (next priority for web search):")
        for t in no_match[:20]:
            print(f"  {t[0]:<11} {t[1]:<22} {t[2] or '':<14} {t[3] or ''}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
