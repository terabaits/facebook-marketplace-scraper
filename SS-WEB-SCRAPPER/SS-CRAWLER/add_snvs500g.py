import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Check if SNVS500G already exists
cur.execute("SELECT id FROM ssd_reference WHERE model ILIKE 'SNVS500G'")
existing = cur.fetchone()

if existing:
    print(f"SSD SNVS500G already exists with ID: {existing[0]}")
else:
    # Add the new SSD
    # Kingston SNVS500G is a 500GB NVMe SSD (NV1 series)
    cur.execute("""
        INSERT INTO ssd_reference (
            brand, model, interface, form_factor, capacity_gb, 
            controller, configuration, has_dram, hmb,
            nand_brand, nand_type, layers,
            read_speed_mb, write_speed_mb, category, notes,
            search_keywords, normalized_name
        ) VALUES (
            'Kingston', 'SNVS500G',
            'PCIe 3.0 x4/NVMe', 'M.2', 500,
            'Phison E13T', 'Single-core, 4-ch, 4-CE/ch', False, True,
            'Toshiba/Kioxia', 'TLC', '112',
            2100, 1700, 'Entry-Level NVMe', 'NV1 series, DRAMless with HMB',
            ARRAY['snvs500g', 'kingston snvs500g', 'kingston nv1', 'nv1', 'snvs', '500g'],
            'kingston snvs500g'
        )
        RETURNING id
    """)
    new_id = cur.fetchone()[0]
    print(f"Added Kingston SNVS500G with ID: {new_id}")

conn.commit()
cur.close()
conn.close()
print("Done!")
