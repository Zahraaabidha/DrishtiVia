"""
Downloads the Indian Helmet Detection dataset directly — no account needed.
Run this FIRST, then run train_helmet.py
"""
import urllib.request
import zipfile
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Public helmet datasets (try in order)
SOURCES = [
    {
        "name": "Helmet Detection (Roboflow Universe public export)",
        "url": "https://public.roboflow.com/ds/zRvBtTRJMv?key=jPVfEBFfnb",
        "file": "helmet_dataset.zip",
    },
    {
        "name": "Safety Helmet Dataset (GitHub)",
        "url": "https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset/archive/refs/heads/master.zip",
        "file": "safety_helmet.zip",
    },
]

def try_download(url, dest, name):
    print(f"Trying: {name}")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            data = b""
            chunk = 1024 * 64
            downloaded = 0
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                data += buf
                downloaded += len(buf)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.0f}% ({downloaded//1024} KB)", end="", flush=True)
        print()
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

print("="*60)
print("ViolaVision — Helmet Dataset Download")
print("="*60)
print()

# Best option: use pip roboflow if installed
try:
    import roboflow
    print("Roboflow package found. Downloading dataset...")
    print()
    print("Go to https://universe.roboflow.com/")
    print("Search: 'helmet detection india'")
    print("Click Export > YOLOv8 > Download zip")
    print("Save the zip to:", os.path.join(BASE, "helmet_dataset.zip"))
    print()
    print("OR: run this with your free Roboflow API key:")
    print('   rf = Roboflow(api_key="YOUR_KEY")')
    print('   project = rf.workspace("roboflow-universe-projects").project("helmet-detection-v3ppx")')
    print('   dataset = project.version(1).download("yolov8")')
    print()
    sys.exit(0)
except ImportError:
    pass

# Fallback: try direct download
zip_path = os.path.join(BASE, "helmet_dataset.zip")
for source in SOURCES:
    dest = os.path.join(BASE, source["file"])
    if try_download(source["url"], dest, source["name"]):
        print(f"Extracting {dest}...")
        try:
            with zipfile.ZipFile(dest, 'r') as z:
                z.extractall(os.path.join(BASE, "helmet_dataset"))
            print("Extracted to helmet_dataset/")
            print("\nNext: run python train_helmet.py")
            break
        except Exception as e:
            print(f"Extraction failed: {e}")
else:
    print()
    print("="*60)
    print("MANUAL DOWNLOAD INSTRUCTIONS (fastest option):")
    print("="*60)
    print()
    print("1. Open this URL in your browser:")
    print("   https://universe.roboflow.com/roboflow-universe-projects/helmet-detection-v3ppx")
    print()
    print("2. Click 'Download Dataset'")
    print("3. Choose Format: YOLOv8")
    print("4. Click 'Download zip to computer'")
    print(f"5. Unzip it into: {os.path.join(BASE, 'helmet_dataset')}")
    print()
    print("6. Then run: python train_helmet.py")
    print()
    print("The folder should contain:")
    print("  helmet_dataset/")
    print("    train/images/  train/labels/")
    print("    valid/images/  valid/labels/")
    print("    data.yaml")
