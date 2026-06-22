"""
Fine-tunes YOLOv8s on the wrong-side driving dataset.
Run: python train_wrongside.py
Classes: right-side (safe), wrong-side (violation)
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def train():
    from ultralytics import YOLO
    import torch

    data_yaml = os.path.join(BASE_DIR, "wrongside_dataset", "data.yaml")
    if not os.path.exists(data_yaml):
        print(f"ERROR: Dataset not found at {data_yaml}")
        sys.exit(1)

    print("ViolaVision — Wrong-Side Driving Model Fine-tuning")
    print(f"Dataset: {data_yaml}")
    print("Classes: right-side (compliant), wrong-side (violation)\n")

    if not torch.cuda.is_available():
        print("WARNING: No GPU detected. Training on CPU will take many hours.")
        response = input("Continue on CPU? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    else:
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print("Estimated training time: ~45-60 minutes\n")

    model = YOLO("yolov8s.pt")

    device = 0 if torch.cuda.is_available() else "cpu"

    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=640,
        batch=8,
        workers=2,
        device=device,
        patience=10,
        save=True,
        project="runs/wrongside_train",
        name="violavision_wrongside_v1",
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        weight_decay=0.0005,
        augment=True,
        mosaic=1.0,
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.4,
        verbose=True,
    )

    best_model = results.save_dir / "weights" / "best.pt"
    print(f"\nTraining complete!")
    print(f"Best model: {best_model}")
    print(f"mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    return str(best_model)

def validate(model_path):
    from ultralytics import YOLO
    import torch
    data_yaml = os.path.join(BASE_DIR, "wrongside_dataset", "data.yaml")
    model = YOLO(model_path)
    device = 0 if torch.cuda.is_available() else "cpu"
    metrics = model.val(data=data_yaml, device=device)
    print(f"\nValidation:")
    print(f"  mAP50:    {metrics.box.map50:.3f}")
    print(f"  mAP50-95: {metrics.box.map:.3f}")
    print(f"  Precision:{metrics.box.mp:.3f}")
    print(f"  Recall:   {metrics.box.mr:.3f}")

if __name__ == "__main__":
    best = train()
    validate(best)
    print(f"\nDone! Add to app.py:")
    print(f"  WRONGSIDE_MODEL_PATH = r'{best}'")
