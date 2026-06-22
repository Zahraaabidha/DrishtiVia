"""
Downloads real traffic photos for ViolaVision testing.
Run: python download_test_images.py
"""
import urllib.request
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

# Unsplash Source API — returns real photos, no auth required, no rate limit for single downloads
IMAGES = [
    # motorcycles on road
    ("https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=1280&q=80", "real_traffic_1.jpg"),
    ("https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=1280&q=80", "real_traffic_2.jpg"),
    ("https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1280&q=80", "real_traffic_3.jpg"),
    # busy road with cars and people
    ("https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=1280&q=80", "real_traffic_4.jpg"),
    ("https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1280&q=80", "real_traffic_5.jpg"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("Downloading real traffic images for ViolaVision...\n")
success = 0
for url, fname in IMAGES:
    dest = os.path.join(OUT, fname)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        size_kb = len(data) // 1024
        print(f"  [OK] {fname}  ({size_kb} KB)")
        success += 1
    except Exception as e:
        print(f"  [FAIL] {fname}: {e}")

print(f"\n{success}/{len(IMAGES)} images downloaded to: {OUT}")
if success > 0:
    print("\nNext: Open ViolaVision at localhost:8501")
    print("      Go to 'Live Detection' tab → upload any of the real_traffic_*.jpg files")
