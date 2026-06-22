"""
Creates synthetic test images with motorcycles, persons, and cars
so you have guaranteed detections even without real photos.
Run once: python create_test_images.py
"""
import cv2
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT, exist_ok=True)

def draw_motorcycle(img, x, y, scale=1.0):
    """Draw a simple motorcycle shape."""
    col = (60, 60, 180)
    # body
    cv2.ellipse(img, (x, y), (int(40*scale), int(15*scale)), 0, 0, 360, col, -1)
    # wheels
    cv2.circle(img, (x-int(30*scale), y+int(15*scale)), int(14*scale), (30,30,30), -1)
    cv2.circle(img, (x+int(30*scale), y+int(15*scale)), int(14*scale), (30,30,30), -1)
    # handlebar
    cv2.line(img, (x+int(20*scale), y-int(10*scale)),
             (x+int(35*scale), y-int(25*scale)), col, int(4*scale))

def draw_person(img, x, y, scale=1.0, helmet=False):
    """Draw a stick person on a motorcycle."""
    head_col = (200, 160, 120)
    body_col = (80, 120, 200)
    helmet_col = (50, 50, 50) if helmet else None
    # head
    cv2.circle(img, (x, y-int(45*scale)), int(12*scale), head_col, -1)
    if helmet:
        cv2.ellipse(img, (x, y-int(48*scale)),
                    (int(14*scale), int(16*scale)), 0, 180, 360,
                    (40, 40, 40), -1)
    # body
    cv2.rectangle(img,
                  (x-int(10*scale), y-int(33*scale)),
                  (x+int(10*scale), y-int(5*scale)),
                  body_col, -1)

def draw_car(img, x, y, scale=1.0):
    """Draw a simple car."""
    col = (100, 180, 80)
    # body
    cv2.rectangle(img,
                  (x-int(50*scale), y-int(20*scale)),
                  (x+int(50*scale), y+int(20*scale)),
                  col, -1)
    # roof
    cv2.rectangle(img,
                  (x-int(30*scale), y-int(40*scale)),
                  (x+int(30*scale), y-int(20*scale)),
                  (80, 150, 60), -1)
    # wheels
    for wx in [x-int(35*scale), x+int(35*scale)]:
        cv2.circle(img, (wx, y+int(20*scale)), int(12*scale), (30,30,30), -1)

def road_background(h=720, w=1280):
    img = np.ones((h, w, 3), dtype=np.uint8) * 120  # grey road
    # sky
    img[:200] = [180, 210, 240]
    # road markings
    for x in range(0, w, 120):
        cv2.rectangle(img, (x, 350), (x+60, 370), (220, 220, 180), -1)
    # footpath
    cv2.rectangle(img, (0, 500), (w, 540), (180, 170, 150), -1)
    # stop line
    cv2.line(img, (0, 400), (w, 400), (255, 255, 255), 5)
    cv2.putText(img, "STOP", (w//2-40, 395),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    return img

# ── Image 1: Two motorcycles, riders without helmets ─────────────────────────
img1 = road_background()
draw_motorcycle(img1, 400, 390)
draw_person(img1, 400, 370, helmet=False)    # no helmet
draw_person(img1, 420, 370, helmet=False)    # second rider — no helmet

draw_motorcycle(img1, 750, 380)
draw_person(img1, 750, 360, helmet=False)    # no helmet
draw_person(img1, 770, 360, helmet=False)
draw_person(img1, 730, 360, helmet=False)    # triple riding

cv2.putText(img1, "Bengaluru Silk Board Junction — Test Image 1",
            (30, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
cv2.imwrite(os.path.join(OUT, "test_helmet_violation.jpg"), img1)
print("Saved: test_helmet_violation.jpg")

# ── Image 2: Car crossing stop line ──────────────────────────────────────────
img2 = road_background()
draw_car(img2, 500, 430)   # car past stop-line (y=400)
draw_motorcycle(img2, 300, 370)
draw_person(img2, 300, 350, helmet=True)   # one rider WITH helmet (ok)

cv2.putText(img2, "Bengaluru KR Circle — Test Image 2",
            (30, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
cv2.imwrite(os.path.join(OUT, "test_stopline_violation.jpg"), img2)
print("Saved: test_stopline_violation.jpg")

# ── Image 3: Busy junction, mixed ────────────────────────────────────────────
img3 = road_background()
for i, (px, helmet) in enumerate([(200,False),(350,False),(500,True),(650,False),(900,False)]):
    draw_motorcycle(img3, px, 360+i*5)
    draw_person(img3, px, 340+i*5, helmet=helmet)
draw_car(img3, 800, 450)
draw_car(img3, 1050, 390)

cv2.putText(img3, "Bengaluru Hebbal Flyover — Test Image 3",
            (30, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
cv2.imwrite(os.path.join(OUT, "test_busy_junction.jpg"), img3)
print("Saved: test_busy_junction.jpg")

print("\nAll test images saved to the 'data' folder.")
print("Upload them in the ViolaVision Live Detection tab.")
