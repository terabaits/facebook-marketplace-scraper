"""Test the save flow end-to-end with a simulated mod session."""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

import psycopg2
from app import app


def main():
    # Create a test session for the mod user (id=4)
    conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                            user="crawler", password="crawler_pass")
    cur = conn.cursor()
    token = uuid.uuid4().hex
    expires = datetime.utcnow() + timedelta(days=1)
    cur.execute("DELETE FROM user_sessions WHERE user_id = 4")
    cur.execute(
        "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (4, token, expires),
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Created session token: {token}")

    # Test the save endpoint
    client = app.test_client()
    client.set_cookie("session_token", token)

    # 1) Save a new model_number for id=13 (Acer Aspire 3)
    print("\n--- Test 1: save model_number for Acer Aspire 3 ---")
    r = client.post("/api/laptop-reference/save", json={
        "brand": "Acer",
        "model": "Aspire 3",
        "model_number": "TEST-SAVE-A315",
        "display_size": "15.6",
        "material": "Plastic",
    })
    print(f"  Save response: {r.status_code}")
    body = r.data.decode("utf-8")
    print(f"  Body: {body[:300]}")

    # 2) Verify
    conn = psycopg2.connect(host="localhost", port=5433, database="ss_market",
                            user="crawler", password="crawler_pass")
    cur = conn.cursor()
    cur.execute("SELECT id, model, model_number FROM laptop_reference WHERE id = 13")
    rows = cur.fetchall()
    print(f"  After save: {rows}")

    # 3) Cleanup: clear the test value
    cur.execute("UPDATE laptop_reference SET model_number = NULL WHERE id = 13")
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
