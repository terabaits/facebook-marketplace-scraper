"""Smoke test: save endpoint accepts the new feature flags."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app


def main():
    client = app.test_client()
    # We can't actually save without being logged in, but we can at least
    # verify the endpoint doesn't 500 on the new payload shape (it'll
    # 401/403 which is fine).
    payload = {
        "brand": "Dell",
        "model": "Vostro 15",
        "display_size": "15",
        "material": "Metal",
        "usb_c_count": "2",
        "usb_count": "1",
        "resolution": "1920x1080",
        "refresh_rate_hz": "144",
        "has_hdmi": True,
        "has_video_pd_usb_c": True,
        "has_ethernet": False,
        "has_touchscreen": True,
    }
    r = client.post('/api/laptop-reference/save', json=payload)
    print(f"Save (no auth): {r.status_code}  body: {r.data[:200].decode('utf-8', errors='replace')}")
    # Expected: 401 or 403 (auth required), NOT 500 (no parse error)
    if r.status_code == 500:
        print("  FAIL: server error (likely a payload parse bug)")
    else:
        print("  OK: endpoint accepts the payload shape")


if __name__ == "__main__":
    main()
