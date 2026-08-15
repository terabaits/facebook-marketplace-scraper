"""Backfill computer_listings build_type/is_prebuilt using the current heuristic."""
import re
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def classify_build_type(title, description):
    """Mirror of ComputerScraper._classify_build_type (updated 2026-07-30)."""
    text = (title or "") + " " + (description or "")
    text_lower = text.lower()

    # Buying ads are not prebuilt PCs for sale
    if re.search(r'pērk|покупаю|kuplyu|perku|buying', text_lower):
        return 'custom'

    # Component-only / part-out markers
    component_only_markers = [
        'viena detaļa', 'viena dala', ' одна деталь',
        'cpu only', 'gpu only', 'ram only', 'ssd only', 'hdd only', 'motherboard only',
        'procesors tikai', 'videokarte tikai', 'ram tikai', 'ssd tikai', 'hdd tikai',
        'pārdodu atsevišķi', 'pārdodu atseviski', 'продаю отдельно',
        'pārdod atsevišķi', 'pārdod atseviski',
        'rezerves daļām', 'rezerves dalam', 'на запчасти', 'for parts'
    ]
    if any(marker in text_lower for marker in component_only_markers):
        return 'custom'

    prebuilt_keywords = [
        'gatavs dators', 'gatavs pc', 'gatava stacija', 'gatavs komplekts',
        'ready pc', 'prebuilt', 'complete pc', 'gaming pc', 'gaming computer',
        'darba stacija', 'ofisa dators', 'mājas dators', 'spēļu dators',
        'gatavs', 'izgatavots', 'komplekts', 'sistēmas bloks', 'sistemas bloks',
        'sistēma', 'system unit', 'desktop pc', 'tower pc',
        'dators komplekts', 'datoru komplekts', 'pc komplekts', 'gaming datoru', 'gaming dators',
        'готовый пк', 'готовый компьютер', 'игровой пк', 'игровой компьютер',
        'системный блок', 'комплект', 'готовый', 'рабочая станция',
        'офисный компьютер', 'домашний компьютер', 'продаю компьютер', 'продается компьютер'
    ]
    if any(kw in text_lower for kw in prebuilt_keywords):
        return 'prebuilt'

    strong_prebuilt_markers = [
        'gatavs dators', 'gatavs pc', 'gatava stacija', 'gatavs komplekts',
        'pilnībā gatavs', 'pilniba gatavs', 'pilnīgi gatavs', 'pilnigi gatavs',
        'izgatavots dators', 'izgatavots pc',
        'ready pc', 'prebuilt', 'complete pc', 'gaming pc', 'gaming computer',
        'darba stacija', 'ofisa dators', 'mājas dators', 'majas dators', 'spēļu dators', 'speļu dators',
        'sistēmas bloks', 'sistemas bloks', 'sistēma', 'system unit',
        'desktop pc', 'tower pc', 'pc tower', 'full pc',
        'готовый пк', 'готовый компьютер', 'игровой пк', 'игровой компьютер',
        'системный блок', 'рабочая станция', 'офисный компьютер', 'домашний компьютер'
    ]
    if any(marker in text_lower for marker in strong_prebuilt_markers):
        return 'prebuilt'

    cpu = bool(re.search(r'(procesors?|cpu|процессор|core\s+i|ryzen|xeon|athlon|pentium)', text_lower))
    gpu = bool(re.search(r'(videokarte?|gpu|video|видеокарта|rx\s*\d|gtx\s*\d|rtx\s*\d|quadro)', text_lower))
    ram = bool(re.search(r'(operatīv|operativa|ram|ddr\d?|оператив)', text_lower))
    storage = bool(re.search(r'(ssd|hdd|m\.\s*2|накопитель)', text_lower))
    motherboard = bool(re.search(r'(pamat plate|motherboard|mobo|материнская|matere)', text_lower))
    psu = bool(re.search(r'(barošanas|barosanas|psu|power\s*supply|блок\s*питания|watt)', text_lower))
    case = bool(re.search(r'(korpuss?|case\b|tower|корпус)', text_lower))

    core_components = sum([cpu, gpu, ram, storage, motherboard, psu, case])
    if core_components >= 5:
        return 'prebuilt'
    if core_components >= 3:
        weak_prebuilt_markers = [
            'gatav', 'komplekt', 'izgatavots', 'system unit', 'sistēmas bloks', 'sistemas bloks',
            'комплект', 'системный блок'
        ]
        if any(marker in text_lower for marker in weak_prebuilt_markers):
            return 'prebuilt'

    return 'custom'


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT listing_id, title, description
        FROM computer_listings
    """)
    rows = cursor.fetchall()
    print(f"Loaded {len(rows)} computer listings")

    updates = []
    counts = {'prebuilt': 0, 'custom': 0, 'office': 0}
    for row in rows:
        bt = classify_build_type(row['title'], row['description'])
        counts[bt] = counts.get(bt, 0) + 1
        updates.append((bt, bt == 'prebuilt', row['listing_id']))

    cursor.executemany("""
        UPDATE computer_listings
        SET build_type = %s, is_prebuilt = %s, updated_at = NOW()
        WHERE listing_id = %s
    """, updates)
    conn.commit()

    cursor.close()
    conn.close()
    print(f"Updated {len(updates)} rows: {counts}")


if __name__ == '__main__':
    main()
