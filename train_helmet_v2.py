from roboflow import Roboflow
from ultralytics import YOLO
import os


def main():
    # Roboflow dataset download
    rf = Roboflow(api_key="rx8fj3LpPjfhQnGmLAOc")

    project = rf.workspace("radya-ai").project("helmet-violation-detection-zgzh1")
    version = project.version(11)
    dataset = version.download("yolov8")

    # Load pretrained YOLOv8s
    model = YOLO("yolov8s.pt")

    # Train
    model.train(
        data=os.path.join(dataset.location, "data.yaml"),
        epochs=40,
        imgsz=640,
        batch=16,
        name="helmet_v2",
        project="runs/detect",
        device=0,          # RTX 3050
        workers=0,         # fixes Windows multiprocessing issue
        patience=10,
        exist_ok=True,
        pretrained=True,
    )

    print("\nTraining complete!")
    print("Best model should be located at:")
    print("runs/detect/helmet_v2/weights/best.pt")


if __name__ == "__main__":
    main()