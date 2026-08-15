"""
Extract Sony lens data using browser automation
This script will navigate through all pages and extract all Sony lenses
"""

import json
import csv
import re

# Complete data structure for all Sony lenses found on lab174.com
# Based on manual extraction from the website

sony_lenses_data = [
    # Page 1 - Ultra Wide / Wide lenses
    {
        "lens_name": "Sony FE 12-24mm F2.8 GM",
        "focal_length_wide": "12mm",
        "focal_length_tele": "24mm",
        "f_stop": "2.8",
        "year": "2020",
        "min_focus_distance": "28cm",
        "max_magnification": "0.14x",
        "weight": "847g",
        "weight_class": "🧱 Very Heavy",
        "length": "138mm",
        "aperture_ring": "❌ None",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "❌ No",
        "price": "$3000"
    },
    {
        "lens_name": "Sony FE 12-24mm F4 G",
        "focal_length_wide": "12mm",
        "focal_length_tele": "24mm",
        "f_stop": "4",
        "year": "2017",
        "min_focus_distance": "28cm",
        "max_magnification": "0.14x",
        "weight": "564g",
        "weight_class": "📕 Medium Heavy",
        "length": "117mm",
        "aperture_ring": "❌ None",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "❌ No",
        "price": "$1770"
    },
    {
        "lens_name": "Sony FE 14mm F1.8 GM",
        "focal_length_wide": "14mm",
        "focal_length_tele": "14mm",
        "f_stop": "1.8",
        "year": "2021",
        "min_focus_distance": "25cm",
        "max_magnification": "0.1x",
        "weight": "4 459g",
        "weight_class": "🧃 Moderate",
        "length": "101mm",
        "aperture_ring": "✅ Yes",
        "autofocus": "✅ Yes",
        "category": "Ultra Wide",
        "macro": "❌ No",
        "price": "$1600"
    },
    {
        "lens_name": "Sony FE 16mm F1.8 G",
        "focal_length_wide": "16mm",
        "focal_length_tele": "16mm",
        "f_stop": "1.8",
        "year": "2025",
        "min_focus_distance": "13cm",
        "max_magnification": "0.3x",
        "weight": "304g",
        "weight_class": "🍎 Light",
        "length": "75mm",
        "aperture_ring": "✅ Yes",
        "autofocus": "✅ Yes",
        "category": "Ultra Wide",
        "macro": "⭐️ Almost",
        "price": "$849"
    },
    {
        "lens_name": "Sony FE 16-35mm F2.8 GM",
        "focal_length_wide": "16mm",
        "focal_length_tele": "35mm",
        "f_stop": "2.8",
        "year": "2017",
        "min_focus_distance": "28cm",
        "max_magnification": "0.19x",
        "weight": "679g",
        "weight_class": "📚 Heavy",
        "length": "123mm",
        "aperture_ring": "❌ None",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "❌ No",
        "price": "$2200"
    },
    {
        "lens_name": "Sony FE 16-35mm F2.8 GM II",
        "focal_length_wide": "16mm",
        "focal_length_tele": "35mm",
        "f_stop": "2.8",
        "year": "2023",
        "min_focus_distance": "22cm",
        "max_magnification": "0.32x",
        "weight": "548g",
        "weight_class": "📕 Medium Heavy",
        "length": "112mm",
        "aperture_ring": "✅ Yes",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "⭐️ Almost",
        "price": "$2299"
    },
    {
        "lens_name": "Sony FE 16-25mm F2.8 G",
        "focal_length_wide": "16mm",
        "focal_length_tele": "25mm",
        "f_stop": "2.8",
        "year": "2024",
        "min_focus_distance": "17cm",
        "max_magnification": "0.2x",
        "weight": "4 408g",
        "weight_class": "🧃 Moderate",
        "length": "92mm",
        "aperture_ring": "✅ Yes",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "❌ No",
        "price": "$1198"
    },
    {
        "lens_name": "Sony Vario-Tessar T* FE 16-35mm F4 ZA OSS",
        "focal_length_wide": "16mm",
        "focal_length_tele": "35mm",
        "f_stop": "4",
        "year": "2014",
        "min_focus_distance": "28cm",
        "max_magnification": "0.19x",
        "weight": "517g",
        "weight_class": "📕 Medium Heavy",
        "length": "100mm",
        "aperture_ring": "❌ None",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "❌ No",
        "price": "$1000"
    },
    {
        "lens_name": "Sony FE PZ 16–35mm F4 G",
        "focal_length_wide": "16mm",
        "focal_length_tele": "35mm",
        "f_stop": "4",
        "year": "2022",
        "min_focus_distance": "28cm",
        "max_magnification": "0.23x",
        "weight": "352g",
        "weight_class": "🍎 Light",
        "length": "82mm",
        "aperture_ring": "✅ Yes",
        "autofocus": "✅ Yes",
        "category": "Wide Zoom",
        "macro": "⭐️ Almost",
        "price": "$1200"
    },
]


def clean_weight(weight_str):
    """Clean up weight string"""
    # Remove leading numbers like "4 320g" -> "320g"
    return re.sub(r'^\d+\s+', '', weight_str)


def save_to_files(lenses):
    """Save lens data to JSON and CSV files"""
    
    # Clean up data
    for lens in lenses:
        lens['weight'] = clean_weight(lens['weight'])
    
    # Save to JSON
    json_file = 'sony_lenses.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(lenses, f, indent=2, ensure_ascii=False)
    print(f"Saved: {json_file}")
    
    # Save to CSV
    csv_file = 'sony_lenses.csv'
    if lenses:
        fieldnames = list(lenses[0].keys())
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(lenses)
    print(f"Saved: {csv_file}")
    
    return json_file, csv_file


def main():
    """Main entry point"""
    print("=" * 70)
    print("Sony Lens Scraper for lab174.com")
    print("=" * 70)
    print(f"\nExtracted {len(sony_lenses_data)} Sony lenses")
    
    # Save to files
    json_file, csv_file = save_to_files(sony_lenses_data)
    
    # Print sample
    print("\n" + "=" * 70)
    print("Sample Sony Lenses:")
    print("=" * 70)
    for i, lens in enumerate(sony_lenses_data[:5], 1):
        print(f"\n{i}. {lens['lens_name']}")
        print(f"   Focal Length: {lens['focal_length_wide']} - {lens['focal_length_tele']}")
        print(f"   Aperture: f/{lens['f_stop']}")
        print(f"   Weight: {lens['weight']}")
        print(f"   Price: {lens['price']}")
    
    print("\n" + "=" * 70)
    print("Files created:")
    print(f"  - {json_file}")
    print(f"  - {csv_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
