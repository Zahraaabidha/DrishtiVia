"""
Fine-tunes YOLOv8n on a helmet/no-helmet dataset.
Run: python train_helmet.py
Requires: pip install roboflow ultralytics
RTX 3050 — training takes ~2 hours for 50 epochs.
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Step 1: Download helmet dataset from Roboflow (no account needed) ──────
# Using the public Indian Helmet Detection dataset
# Dataset: helmet + no-helmet classes on Indian roads

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helmet_dataset")

def download_dataset():
    """Download helmet dataset using roboflow or fallback to direct download."""
    print("Downloading helmet detection dataset...")

    try:
        from roboflow import Roboflow
        # Public dataset — no API key needed for download
        rf = Roboflow(api_key="")
        project = rf.workspace("joseph-nelson").project("helmet-detection-yolov8-pgua6")
        dataset = project.version(1).download("yolov8", location=DATASET_DIR)
        print(f"Dataset downloaded to {DATASET_DIR}")
        return os.path.join(DATASET_DIR, "data.yaml")
    except Exception as e:
        print(f"Roboflow download failed: {e}")
        print("Falling back to manual dataset creation...")
        return create_manual_dataset()

def create_manual_dataset():
    """
    Create a minimal dataset.yaml pointing to downloaded images.
    Uses the Indian Helmet Detection dataset from GitHub.
    """
    import urllib.request
    import zipfile

    zip_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco8.zip"
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coco8.zip")

    print("Downloading sample dataset for structure...")
    urllib.request.urlretrieve(zip_url, zip_path)

    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(os.path.dirname(os.path.abspath(__file__)))

    # Point to coco8 as placeholder — replace with real helmet data
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "coco8", "coco8.yaml")

# ── Step 2: Train ───────────────────────────────────────────────────────────
def train(data_yaml):
    from ultralytics import YOLO

    print("\n" + "="*60)
    print("Starting YOLOv8n helmet fine-tuning")
    print("="*60)

    model = YOLO("yolov8m.pt")   # medium: better accuracy than small, ~2-3GB VRAM

    import torch
    device = 0 if torch.cuda.is_available() else "cpu"
    batch  = 16 if torch.cuda.is_available() else 4

    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=640,
        batch=batch,
        device=device,
        patience=10,         # early stopping
        save=True,
        project="runs/helmet_train",
        name="violavision_v1",
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        weight_decay=0.0005,
        augment=True,
        mosaic=1.0,
        degrees=10.0,        # more rotation variety for side-angle cameras
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        hsv_h=0.015,         # hue shift — handles different lighting/time of day
        hsv_s=0.5,           # saturation — helps night vs day generalisation
        hsv_v=0.4,           # brightness — critical for night footage accuracy
        verbose=True,
    )

    best_model = results.save_dir / "weights" / "best.pt"
    print(f"\nTraining complete!")
    print(f"Best model saved at: {best_model}")
    print(f"mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    return str(best_model)

# ── Step 3: Validate ────────────────────────────────────────────────────────
def validate(model_path, data_yaml):
    from ultralytics import YOLO
    model = YOLO(model_path)
    metrics = model.val(data=data_yaml, device=0)
    print(f"\nValidation results:")
    print(f"  mAP50:    {metrics.box.map50:.3f}")
    print(f"  mAP50-95: {metrics.box.map:.3f}")
    print(f"  Precision:{metrics.box.mp:.3f}")
    print(f"  Recall:   {metrics.box.mr:.3f}")

if __name__ == "__main__":
    print("ViolaVision — Helmet Model Fine-tuning")
    print("Dataset: HELMET INDIA (530 train / 66 valid)")
    print("Classes: With Helmet, Without Helmet\n")

    import torch
    if not torch.cuda.is_available():
        print("WARNING: No GPU detected. Training on CPU will take ~8 hours.")
        response = input("Continue on CPU? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    else:
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print("Estimated training time: ~1.5-2 hours\n")

    # Use the already-downloaded dataset
    data_yaml = os.path.join(BASE_DIR, "helmet_dataset", "data.yaml")
    if not os.path.exists(data_yaml):
        print(f"ERROR: Dataset not found at {data_yaml}")
        print("Make sure helmet_dataset/ folder is inside violavision/")
        sys.exit(1)

    print(f"Using dataset: {data_yaml}")
    best_model = train(data_yaml)
    validate(best_model, data_yaml)

    print(f"\nDone! Best model: {best_model}")
    print("Update app.py line 56: YOLO('yolov8n.pt') -> YOLO('" + best_model + "')")
