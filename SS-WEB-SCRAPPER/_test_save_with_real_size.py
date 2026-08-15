"""Test save with the correct display_size to confirm UPSERT matches."""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2
from app import app


def main():
    # Create a session for mod user (id=4)
    conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                            user="crawler", password="crawler_pass")
    cur = conn.cursor()
    token = uuid.uuid4().hex
    cur.execute("DELETE FROM user_sessions WHERE user_id = 4")
    cur.execute(
        "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (4, token, datetime.utcnow() + timedelta(days=1)),
    )
    conn.commit()
    cur.close()
    conn.close()

    client = app.test_client()
    client.set_cookie("session_token", token)

    # Use the ACTUAL display_size from row 13 (15")
    print("--- Test: save with correct display_size ---")
    r = client.post("/api/laptop-reference/save", json={
        "brand": "Acer",
        "model": "Aspire 3",
        "model_number": "TEST-CORRECT-A315",
        "display_size": '15"',
    })
    print(f"  Save response: {r.status_code}")
    body = r.data.decode("utf-8")
    # Find the id in the response
    import re
    id_match = re.search(r'"id":(\d+)', body)
    print(f"  Returned id: {id_match.group(1) if id_match else '?'}")

    # Verify
    conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                            user="crawler", password="crawler_pass")
    cur = conn.cursor()
    cur.execute("SELECT id, model, model_number FROM laptop_reference WHERE model_number = 'TEST-CORRECT-A315'")
    print("  Rows with that model_number:")
    for r2 in cur.fetchall():
        print(f"    {r2}")
    # Cleanup
    cur.execute("DELETE FROM laptop_reference WHERE model_number = 'TEST-CORRECT-A315'")
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
