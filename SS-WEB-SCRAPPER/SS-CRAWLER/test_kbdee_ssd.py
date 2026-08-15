#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug SSD matching for kbdee.html - Kingston 1TB SSD m.2 NVMe."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import get_db_manager, init_database
from src.database.repository import SSDReferenceRepository
from src.scraper.ssd_matcher import SSDMatcher
from src.utils.text import normalize_text
from src.utils.config import AppConfig

# Full listing text from kbdee.html
listing_text = """Rtx5070 12Gb. Corsair Vengeance Ddr5 32Gb. Intel Core I7-14700Kf.

Pardodu jaudigu, modernu, super klusu un stabilu gaming datoru.

Dators ir ideala stavokli, bez defektiem, viss darbojas perfekti. Videokarte ir pilnigi jauna, pirms divam dienam iznemta no iepakojuma, ir aktiva razotaja garantija lidz 2029. gadam.

Vizuali, protams, nav skaistakais, bet jaudas zina neatstav vienaldzigu. Korpusam nav prieksejais stiklinjs.

Lieliski piemerots spelesanai, darbam, montazai un parejam.

Specifikacijas:

GPU: MSI GeForce RTX 5070 Dual OC White 12GB

CPU: Intel Core i7-14700KF + BeQuiet Kuleris

RAM: Corsair Vengeance 32GB DDR5 (2x16GB)

Atmina: Kingston 1TB SSD m. 2 NVMe

Matesplate: Asus Prime Z790-A WiFi

Barosanas bloks: Corsair RM1000X uz 1000W

OS: Windows 11 Home

Atrodas Riga, varu tikties klatiene vai nosutit ar kurjera starpniecibu. Iespejama piegade pec vienosanas.

RTX5070 12GB. Corsair Vengeance DDR5 32GB. Intel Core i7-14700KF.

Prodeju moshnij, sovremennij, tihij i stabilnij igrovoj PK.

Komputer v idealnom sostojanii, bez kakih-libo defektov, vse rabotaet otlichno. Videokarta novaja, dva dnja nazad dostal iz upakovki, aktivnaja garantija proizvoditelja do 2029 goda.

Vizualno, mozhet, ne luchshij, no v plane moshnosti ravnodushnim ne ostavit. U korpusa otsutstvujet perednee steklo.

Otlichno podhodit dlja igr, raboty, montazha i prochego.

Harakteristiki:

GPU: MSI GeForce RTX 5070 Dual OC White 12GB

CPU: Intel Core i7-14700KF + BeQuiet kuler

RAM: Corsair Vengeance 32GB DDR5 (2x16GB)

Pamatj: Kingston 1TB SSD m. 2 NVMe

Materinka: Asus Prime Z790-A WiFi

Blok pitanija: Corsair RM1000X na 1000W

OS: Windows 11 Home

Nahoditsja v Rige vozmozhna vstrecha ili otpravka kurjerom. Dostavka po dogovorennosti.

 Procesors:

 I7-14700Kf

 Procesora frekvence, Ghz:

 3.40

 Pamat plate:

 Asus prime z790-a wifi

 Video:

 Rtx 5070

 Operativa atmina, Gb:

 32

 HDD apjoms, Gb:

 1000

 DVD:

 DVD

 Stavoklis:

 lietota

 Cena:

 1 499 €"""

full_text = listing_text
text_lower = full_text.lower()
normalized = normalize_text(full_text)

config = AppConfig()
init_database(config.database)
db = get_db_manager()

def _extract_ssd_capacity(text):
    """Extract SSD capacity from text."""
    import re
    tb_match = re.search(r'(\d+)\s*TB', text, re.IGNORECASE)
    if tb_match:
        return int(tb_match.group(1)) * 1000
    gb_match = re.search(r'(\d+)\s*GB', text, re.IGNORECASE)
    if gb_match:
        return int(gb_match.group(1))
    return None

with db.get_session() as session:
    ssds = SSDReferenceRepository.get_all(session)
    ssd_matcher = SSDMatcher(ssds)
    
    print("="*60)
    print("SSD MATCHER DEBUG FOR kbdEE.html")
    print("="*60)
    print("\nNormalized text preview: {}...".format(normalized[:200]))
    
    ssd_capacity = _extract_ssd_capacity(full_text)
    print("\nExtracted SSD capacity: {} GB".format(ssd_capacity))
    
    print("\n'kingston' in normalized: {}".format('kingston' in normalized))
    print("'kingston' found at position: {}".format(normalized.find('kingston')))
    
    kingston_pos = normalized.find('kingston')
    if kingston_pos != -1:
        start = max(0, kingston_pos - 30)
        end = min(len(normalized), kingston_pos + 50)
        print("\nContext around 'kingston': ...{}...".format(normalized[start:end]))
    
    ssd_keywords = ['ssd', 'nvme', 'm.2', 'm2', 'ciet']
    print("\nSSD keyword check:")
    for kw in ssd_keywords:
        if kw in text_lower:
            print("  '{}' found in text".format(kw))
    
    ssd_match = ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)
    
    print("\n" + "="*60)
    print("MATCH RESULT")
    print("="*60)
    print("Matched SSD: {} (ID: {})".format(
        ssd_match.ssd.model if ssd_match.ssd else 'None', 
        ssd_match.ssd.id if ssd_match.ssd else 'N/A'
    ))
    print("Brand: {}".format(ssd_match.ssd.brand if ssd_match.ssd else 'N/A'))
    print("Capacity: {} GB".format(ssd_match.ssd.capacity_gb if ssd_match.ssd else 'N/A'))
    print("Method: {}".format(ssd_match.method))
    print("Confidence: {}".format(ssd_match.confidence))
    
    if ssd_match.ssd:
        print("\n" + "="*60)
        print("COMPUTER_MATCHER ACCEPTANCE LOGIC")
        print("="*60)
        
        ssd_brand = normalize_text(ssd_match.ssd.brand)
        ssd_model = normalize_text(ssd_match.ssd.model)
        
        print("SSD brand: '{}'".format(ssd_brand))
        print("SSD model: '{}'".format(ssd_model))
        
        has_brand = ssd_brand in normalized
        print("has_brand ('{}' in normalized): {}".format(ssd_brand, has_brand))
        
        has_model_in_text = ssd_model in normalized
        print("has_model_in_text ('{}' in normalized): {}".format(ssd_model, has_model_in_text))
        
        model_parts = ssd_match.ssd.model.split()
        print("\nModel parts check:")
        for part in model_parts:
            part_norm = normalize_text(part)
            if len(part_norm) >= 2:
                found = part_norm in normalized
                print("  '{}' in normalized: {}".format(part_norm, found))
        
        is_exact = ssd_match.method.split('+')[0] == 'exact'
        is_model_part = 'model_part' in ssd_match.method
        is_capacity_match = 'capacity_exact' in ssd_match.method or 'capacity_near' in ssd_match.method
        
        print("\nis_exact: {}".format(is_exact))
        print("is_model_part: {}".format(is_model_part))
        print("is_capacity_match: {}".format(is_capacity_match))
        
        is_specific_ssd = False
        if is_exact:
            is_specific_ssd = True
            print("\nSSD is specific: exact match")
        elif is_model_part and has_brand:
            if has_model_in_text:
                is_specific_ssd = True
                print("\nSSD is specific: model_part + brand + model in text")
            else:
                print("\nSSD NOT specific: model_part + brand but model NOT in text")
        elif is_capacity_match and has_brand:
            print("\nChecking SSD context for brand+capacity...")
            ssd_brand_in_ssd_context = False
            for kw in ['ssd', 'nvme', 'm.2', 'm2', 'ciet']:
                if kw in text_lower:
                    kw_pos = text_lower.find(kw)
                    context_start = max(0, kw_pos - 50)
                    context_end = min(len(text_lower), kw_pos + 50)
                    context = text_lower[context_start:context_end]
                    print("  Context around '{}': ...{}...".format(kw, context))
                    if ssd_brand in context:
                        ssd_brand_in_ssd_context = True
                        print("    -> Brand '{}' found in context!".format(ssd_brand))
                        break
            
            if ssd_brand_in_ssd_context:
                is_specific_ssd = True
                print("\nSSD is specific: brand in SSD context + capacity match")
            else:
                print("\nSSD NOT specific: brand not in SSD context")
        else:
            print("\nSSD NOT specific: no criteria met")
        
        print("\nFinal is_specific_ssd: {}".format(is_specific_ssd))
    
    print("\n" + "="*60)
    print("ALL KINGSTON SSDs IN DATABASE (1TB capacity)")
    print("="*60)
    kingston_ssds = [s for s in ssds if s.brand and s.brand.lower() == 'kingston' and s.capacity_gb == 1000]
    for ssd in sorted(kingston_ssds, key=lambda x: x.model):
        print("  ID {}: {} {} {}GB - Keywords: {}".format(
            ssd.id, ssd.brand, ssd.model, ssd.capacity_gb, ssd.search_keywords
        ))
    
    print("\n" + "="*60)
    print("WHAT SHOULD HAPPEN:")
    print("="*60)
    print("The listing mentions 'Kingston 1TB SSD m.2 NVMe'")
    print("This should match Kingston ID 837 (1TB NVMe) or similar")
    print("\nBut currently matching: Corsair MP600 CORE (ID 392)")
    print("\nPROBLEM: The 'core' from 'Corsair Vengeance' matches 'MP600 CORE'")
    print("and the capacity matches (1000GB), but this is WRONG!")
