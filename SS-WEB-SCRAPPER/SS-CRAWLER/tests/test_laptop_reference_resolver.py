"""Unit tests for laptop reference resolver tolerance rules."""
import os
import sys

# Add project root to path so we can import the module under test
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.scraper.laptop_reference_resolver import (
    normalize_brand,
    normalize_display_size,
    normalize_model,
    normalized_key,
    _extract_resolution_from_description,
)


def t_brand():
    assert normalize_brand('Apple') == 'apple'
    assert normalize_brand('  apple  ') == 'apple'
    assert normalize_brand('APPLE') == 'apple'
    assert normalize_brand('Hp') == 'hp'
    assert normalize_brand('') == ''
    assert normalize_brand(None) == ''
    print('brand: ok')


def t_display_size():
    assert normalize_display_size('13"') == '13'
    assert normalize_display_size('13.0"') == '13.0'  # keep .0 to match existing reference rows
    assert normalize_display_size('13.0') == '13.0'
    assert normalize_display_size('15.6') == '15.6'
    assert normalize_display_size('15.6 inch') == '15.6'
    assert normalize_display_size('15.6 collas') == '15.6'
    assert normalize_display_size('') == ''
    assert normalize_display_size(None) == ''
    assert normalize_display_size('N/A') == ''
    print('display_size: ok')


def t_model_basic():
    assert normalize_model('Macbook Air') == 'macbook air'
    assert normalize_model('  macbook  air  ') == 'macbook air'
    assert normalize_model('MACBOOK AIR') == 'macbook air'
    print('model basic: ok')


def t_model_strip_trailing_size_DISABLED():
    """Trailing-size strip is DISABLED. Many real model names contain the size
    (XPS 13, Cyborg 15, Vivobook Go 15, Macbook Pro 14 M2) and stripping them
    caused 43 false merges in the test dataset. Admin merges via the VALID mark
    handle the few true duplicates.
    """
    # Trailing numbers stay in the model even when they match display_size
    assert normalize_model('Macbook air 13', '13') == 'macbook air 13'
    assert normalize_model('Xps 13', '13') == 'xps 13'
    assert normalize_model('Sword 17', '17') == 'sword 17'
    assert normalize_model('Vivobook go 15', '15') == 'vivobook go 15'
    assert normalize_model('Cyborg 15', '15') == 'cyborg 15'
    # These stay split now (admin can merge via VALID mark)
    print('model trailing-size DISABLED: ok')


def t_model_strip_parens():
    assert normalize_model('Macbook Pro (2019)') == 'macbook pro'
    assert normalize_model('Macbook Pro (M2 2022)') == 'macbook pro'
    assert normalize_model('Pro 13.3 (Touch Bar)') == 'pro 13.3'
    print('model strip-parens: ok')


def t_model_strip_ad_words():
    # English ad-words are NOT stripped (they appear in real product names)
    assert normalize_model('Laptop Macbook Air') == 'laptop macbook air'
    assert normalize_model('Macbook Air Notebook') == 'macbook air notebook'
    assert normalize_model('Gaming Laptop Acer Aspire') == 'gaming laptop acer aspire'
    # "Gaming A15" is a real product line (Asus TUF Gaming A15) - NOT stripped
    assert normalize_model('Gaming A15', None) == 'gaming a15'
    # "Envy Notebook" is HP's product line - NOT stripped
    assert normalize_model('Envy notebook', None) == 'envy notebook'
    # Latvian ad-words ARE stripped
    assert normalize_model('Portatīvais dators Lenovo ThinkPad', None) == 'lenovo thinkpad'
    assert normalize_model('Klēpjdators Acer Aspire', None) == 'acer aspire'
    print('model strip-ad-words: ok')


def t_model_keep_model_tokens():
    # 'M2', 'M3', 'Pro', 'Air' are model tokens, must not be stripped
    assert normalize_model('Macbook Pro 14 M2', '14') == 'macbook pro 14 m2'
    assert normalize_model('Macbook Air M3 2024', None) == 'macbook air m3 2024'
    # 'i5', 'X1' etc. are model tokens
    assert normalize_model('ThinkPad X1 Carbon', None) == 'thinkpad x1 carbon'
    print('model keep-tokens: ok')


def t_model_no_typo_matching():
    # Typos stay split - admin merges these later
    assert normalize_model('Macbook Proo', '15') == 'macbook proo'
    assert normalize_model('Macook Pro', '15') == 'macook pro'
    print('model no-typo: ok')


def t_normalized_key():
    # Case + whitespace collapse
    assert normalized_key('Apple', 'Macbook Air', '13"') == 'apple|macbook air|13'
    assert normalized_key('apple', 'MACBOOK AIR', '13"') == 'apple|macbook air|13'
    # The "Macbook air 13" duplicate stays split (admin merges via VALID)
    assert normalized_key('Apple', 'Macbook air 13', '13"') == 'apple|macbook air 13|13'
    # Different sizes don't merge
    assert normalized_key('Apple', 'Macbook Air', '15"') == 'apple|macbook air|15'
    # Different brands don't merge
    assert normalized_key('Apple', 'Macbook Air', '13"') != normalized_key('HP', 'Macbook Air', '13"')
    # Missing brand or model -> empty key
    assert normalized_key(None, 'Macbook Air', '13') == ''
    assert normalized_key('Apple', None, '13') == ''
    assert normalized_key('Apple', '', '13') == ''
    # No display_size -> just the size part is empty
    assert normalized_key('Apple', 'Macbook Air', None) == 'apple|macbook air|'
    print('normalized_key: ok')


def t_resolution_extract():
    assert _extract_resolution_from_description('Screen 15.6", 1920x1080 IPS') == '1920x1080'
    assert _extract_resolution_from_description('Resolution 2560×1600') == '2560x1600'
    assert _extract_resolution_from_description('2560 x 1600 retina') == '2560x1600'
    # Only first match wins
    assert _extract_resolution_from_description('1920x1080 internal, 3840x2160 external') == '1920x1080'
    # No resolution
    assert _extract_resolution_from_description('plain text') is None
    assert _extract_resolution_from_description(None) is None
    print('resolution extract: ok')


def t_combined_real_examples():
    # Real Apple Macbook Air 13 from the database
    assert normalized_key('Apple', 'Macbook Air', '13"') == 'apple|macbook air|13'
    assert normalized_key('Apple', 'Macbook air', '13"') == 'apple|macbook air|13'  # case-insensitive
    # The "Macbook air 13" duplicate stays split (admin merges via VALID)
    assert normalized_key('Apple', 'Macbook air 13', '13"') == 'apple|macbook air 13|13'
    # Apple part number "Mgn63Ru/a" - stays as-is
    assert normalized_key('Apple', 'Mgn63Ru/a', '13') == 'apple|mgn63ru/a|13'
    # Apple internal model "A1278" - stays as-is, admin can merge later
    assert normalized_key('Apple', 'A1278', '13') == 'apple|a1278|13'
    # Dell XPS 13 keeps "13" (it's the model name, not the size)
    assert normalized_key('Dell', 'Xps 13', '13"') == 'dell|xps 13|13'
    # MSI Cyborg 15 keeps "15" (model name)
    assert normalized_key('Msi', 'Cyborg 15', '15"') == 'msi|cyborg 15|15'
    print('combined real examples: ok')


if __name__ == '__main__':
    t_brand()
    t_display_size()
    t_model_basic()
    t_model_strip_trailing_size_DISABLED()
    t_model_strip_parens()
    t_model_strip_ad_words()
    t_model_keep_model_tokens()
    t_model_no_typo_matching()
    t_normalized_key()
    t_resolution_extract()
    t_combined_real_examples()
    print('\nALL TOLERANCE TESTS PASSED')
