import psycopg2
conn=psycopg2.connect(host='localhost', port=5433, dbname='ss_market', user='crawler', password='crawler_pass')
cur=conn.cursor()
cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'laptop_reference' ORDER BY ordinal_position")
print("=== laptop_reference columns ===")
for r in cur.fetchall(): print(f'  {r[0]:<30} {r[1]:<25} NULL={r[2]}')

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'laptop_listings' ORDER BY ordinal_position")
print("\n=== laptop_listings columns ===")
for r in cur.fetchall(): print(f'  {r[0]:<30} {r[1]}')

cur.execute("""SELECT
    COUNT(*) as total,
    COUNT(material) as material_set,
    COUNT(usb_count) as usb_set,
    COUNT(usb_c_count) as usb_c_set,
    COUNT(hdmi_count) as hdmi_count_set,
    COUNT(resolution) as resolution_set,
    COUNT(refresh_rate_hz) as refresh_set,
    COUNT(has_hdmi) as hdmi_set,
    COUNT(has_video_pd_usb_c) as pd_set,
    COUNT(has_ethernet) as eth_set,
    COUNT(has_touchscreen) as touch_set
FROM laptop_reference""")
print("\n=== laptop_reference fill rates ===")
for r in cur.fetchall():
    for k, v in zip(['total','material','usb_count','usb_c_count','hdmi_count','resolution','refresh_rate_hz','has_hdmi','has_video_pd_usb_c','has_ethernet','has_touchscreen'], r):
        print(f'  {k:<22} {v}')
