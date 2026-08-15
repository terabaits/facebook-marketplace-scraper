"""Unit tests for CPU reference resolver normalization rules."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.scraper.cpu_reference_resolver import (
    normalize_cpu_name,
    _classify_vendor,
)


def t_intel_normalization():
    # Full SKU with uppercase suffix
    assert normalize_cpu_name("Intel Core i7-11400H") == ("Intel", "i7-11400H", "intel|i7-11400h")
    assert normalize_cpu_name("Intel(R) Core(TM) i7-11400H") == ("Intel", "i7-11400H", "intel|i7-11400h")
    assert normalize_cpu_name("Intel(R)Core(TM)i7-11400H") == ("Intel", "i7-11400H", "intel|i7-11400h")
    # Case insensitivity on the suffix letter
    assert normalize_cpu_name("i7-11400h") == ("Intel", "i7-11400H", "intel|i7-11400h")
    assert normalize_cpu_name("I5-1135g7") == ("Intel", "i5-1135G7", "intel|i5-1135g7")
    assert normalize_cpu_name("I5-1135G7") == ("Intel", "i5-1135G7", "intel|i5-1135g7")
    # Multiple-letter suffix
    assert normalize_cpu_name("i9-13900hx") == ("Intel", "i9-13900HX", "intel|i9-13900hx")
    assert normalize_cpu_name("i7-1255u") == ("Intel", "i7-1255U", "intel|i7-1255u")
    # Bare class name (no model)
    assert normalize_cpu_name("Intel Core i5") == ("Intel", "i5", "intel|i5")
    assert normalize_cpu_name("Intel i5") == ("Intel", "i5", "intel|i5")
    assert normalize_cpu_name("I5") == ("Intel", "i5", "intel|i5")
    # Pentium / Celeron / Xeon
    assert normalize_cpu_name("Intel Pentium Gold 7505") == ("Intel", "Pentium Gold 7505", "intel|pentium gold 7505")
    assert normalize_cpu_name("Intel Celeron N4020") == ("Intel", "Celeron N4020", "intel|celeron n4020")
    # Trailing display size (e.g. "i5-1135G7 14") should drop
    assert normalize_cpu_name("i5-1135G7 14") == ("Intel", "i5-1135G7", "intel|i5-1135g7")
    # Clock speed suffix should drop
    assert normalize_cpu_name("Intel Core i5-1135G7 @ 2.40GHz") == ("Intel", "i5-1135G7", "intel|i5-1135g7")
    # "Processor" suffix should drop
    assert normalize_cpu_name("Intel Core i7-11400H Processor") == ("Intel", "i7-11400H", "intel|i7-11400h")
    # "Series" suffix should drop
    assert normalize_cpu_name("Intel Core i5 Series") == ("Intel", "i5", "intel|i5")
    print("intel: ok")


def t_amd_normalization():
    # Full SKU
    assert normalize_cpu_name("AMD Ryzen 7 5800H") == ("AMD", "Ryzen 7 5800H", "amd|ryzen 7 5800h")
    assert normalize_cpu_name("Amd ryzen 5 5500U") == ("AMD", "Ryzen 5 5500U", "amd|ryzen 5 5500u")
    # PRO variant
    assert normalize_cpu_name("AMD Ryzen 7 PRO 4750U") == ("AMD", "Ryzen 7 Pro 4750U", "amd|ryzen 7 pro 4750u")
    # Bare class
    assert normalize_cpu_name("Amd ryzen 5") == ("AMD", "Ryzen 5", "amd|ryzen 5")
    assert normalize_cpu_name("Ryzen 5") == ("AMD", "Ryzen 5", "amd|ryzen 5")
    # With clock speed
    assert normalize_cpu_name("AMD Ryzen 7 5800H @ 4.4GHz") == ("AMD", "Ryzen 7 5800H", "amd|ryzen 7 5800h")
    print("amd: ok")


def t_apple_normalization():
    # Bare M
    assert normalize_cpu_name("M1") == ("Apple", "M1", "apple|m1")
    assert normalize_cpu_name("M2") == ("Apple", "M2", "apple|m2")
    assert normalize_cpu_name("M3") == ("Apple", "M3", "apple|m3")
    # M2 Pro/Max/Ultra
    assert normalize_cpu_name("M2 Pro") == ("Apple", "M2 Pro", "apple|m2 pro")
    assert normalize_cpu_name("M2 Max") == ("Apple", "M2 Max", "apple|m2 max")
    assert normalize_cpu_name("M3 Pro") == ("Apple", "M3 Pro", "apple|m3 pro")
    # Apple prefix
    assert normalize_cpu_name("Apple M2") == ("Apple", "M2", "apple|m2")
    assert normalize_cpu_name("Apple M2 Pro") == ("Apple", "M2 Pro", "apple|m2 pro")
    assert normalize_cpu_name("Apple Silicon M2") == ("Apple", "M2", "apple|m2")
    # Case insensitivity
    assert normalize_cpu_name("m2") == ("Apple", "M2", "apple|m2")
    print("apple: ok")


def t_qualcomm_normalization():
    assert normalize_cpu_name("Snapdragon X Elite") == ("Qualcomm", "Snapdragon X Elite", "qualcomm|snapdragon x elite")
    assert normalize_cpu_name("Qualcomm Snapdragon 8cx Gen 3") == ("Qualcomm", "Snapdragon 8cx Gen 3", "qualcomm|snapdragon 8cx gen 3")
    # Lowercase
    assert normalize_cpu_name("snapdragon x elite") == ("Qualcomm", "Snapdragon X Elite", "qualcomm|snapdragon x elite")
    print("qualcomm: ok")


def t_empty_or_nonsense():
    # These should all return (None, "", "")
    cases = [
        "",
        None,
        "Intel",
        "Processor",
        "CPU",
        "Series",
        "@",
    ]
    for raw in cases:
        result = normalize_cpu_name(raw)
        assert result == (None, "", ""), f"expected (None, '', '') for {raw!r}, got {result}"
    print("empty/nonsense: ok")


def t_classify_vendor():
    assert _classify_vendor("i7-11400H") == "Intel"
    assert _classify_vendor("I5-1135G7") == "Intel"
    assert _classify_vendor("i5") == "Intel"
    assert _classify_vendor("Pentium Gold 7505") == "Intel"
    assert _classify_vendor("Ryzen 7 5800H") == "AMD"
    assert _classify_vendor("ryzen 5") == "AMD"
    assert _classify_vendor("M2") == "Apple"
    assert _classify_vendor("m2 pro") == "Apple"
    assert _classify_vendor("Snapdragon X Elite") == "Qualcomm"
    print("classify_vendor: ok")


def t_real_data_examples():
    """Test against the actual CPU strings we see in the DB."""
    cases = [
        # (raw, expected_brand, expected_model)
        ("Intel Core i5",         "Intel", "i5"),
        ("I5",                    "Intel", "i5"),
        ("Amd ryzen 5",           "AMD",   "Ryzen 5"),
        ("M1",                    "Apple", "M1"),
        ("M2",                    "Apple", "M2"),
        ("Apple M2",              "Apple", "M2"),
        ("Amd ryzen 3",           "AMD",   "Ryzen 3"),
        ("Intel core i5",         "Intel", "i5"),
        ("I5-1135g7",             "Intel", "i5-1135G7"),
        ("I5-12450H",             "Intel", "i5-12450H"),
        ("Intel Core i3",         "Intel", "i3"),
        ("I5-1135G7",             "Intel", "i5-1135G7"),
        ("Intel Core i3-1115g",    "Intel", "i3-1115G"),
        ("Intel Core i5-1135g",    "Intel", "i5-1135G"),
        ("Core i5",               "Intel", "i5"),
        ("Ryzen 5",               "AMD",   "Ryzen 5"),
        ("Ryzen 5 4600H",         "AMD",   "Ryzen 5 4600H"),
        ("Intel Core i5-1135G7 @ 2.40GHz", "Intel", "i5-1135G7"),
    ]
    for raw, exp_brand, exp_model in cases:
        brand, model, _ = normalize_cpu_name(raw)
        assert brand == exp_brand, f"brand for {raw!r}: expected {exp_brand!r}, got {brand!r}"
        assert model == exp_model, f"model for {raw!r}: expected {exp_model!r}, got {model!r}"
    print("real_data_examples: ok")


if __name__ == "__main__":
    t_intel_normalization()
    t_amd_normalization()
    t_apple_normalization()
    t_qualcomm_normalization()
    t_empty_or_nonsense()
    t_classify_vendor()
    t_real_data_examples()
    print("\nALL CPU NORMALIZATION TESTS PASSED")
