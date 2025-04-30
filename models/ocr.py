import cv2
import csv
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from paddleocr import PaddleOCR
from collections import defaultdict, Counter
from dataclasses import dataclass

ocr = PaddleOCR(use_angle_cls=True, lang='en')  

model = YOLO("/license_plate.pt")
tracker = DeepSort(max_age=30)


@dataclass
class Plate:
    text: str
    confidence: float
    track_id: int

class ResultAccumulator:
    def __init__(self):
        self.plate_history = defaultdict(list)
        self.best_confidence = defaultdict(float)

    def add(self, plate: Plate):
        if plate.text:
            self.plate_history[plate.track_id].append(plate.text)
            if plate.confidence > self.best_confidence[plate.track_id]:
                self.best_confidence[plate.track_id] = plate.confidence

    def get_final_plate_texts(self):
        final = {}
        for tid, texts in self.plate_history.items():
            most_common, _ = Counter(texts).most_common(1)[0]
            final[tid] = (most_common, self.best_confidence[tid])
        return final

accumulator = ResultAccumulator()

cap = cv2.VideoCapture("car.mp4")
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    detections = model.predict(frame, verbose=False)[0].boxes.data.cpu().numpy()
    detection_list = [[[d[0], d[1], d[2] - d[0], d[3] - d[1]], d[4], int(d[5])] for d in detections if int(d[5]) == 0]


    tracks = tracker.update_tracks(detection_list, frame=frame)

    for track in tracks:
        if not track.is_confirmed():
            continue
        track_id = track.track_id
        l, t, w, h = track.to_ltrb()
        #x1, y1, x2, y2 = int(l), int(t), int(w), int(h)
        x1, y1, x2, y2 = map(int, track.to_ltrb())

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        # Run PaddleOCR
        ocr_results = ocr.ocr(crop, cls=True)
        if ocr_results and ocr_results[0] is not None:
            text_segments = []
            for line in ocr_results[0]:
                box, (text, conf) = line
                x_center = sum([point[0] for point in box]) / 4
                y_center = sum([point[1] for point in box]) / 4
                text_segments.append((x_center, y_center, text, conf))

            # Sort by x position (left to right), then by y if needed
            text_segments.sort(key=lambda x: (x[1], x[0]))

            full_text = ''.join([t[2].replace(" ", "") for t in text_segments])
            avg_conf = sum([t[3] for t in text_segments]) / len(text_segments)

            accumulator.add(Plate(full_text, avg_conf, track_id))

    frame_count += 1

cap.release()

# Save final results
final = accumulator.get_final_plate_texts()
with open("final_license_plate_results.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Track ID", "Most Frequent Plate Text", "Best Confidence"])
    for tid, (plate, conf) in final.items():
        writer.writerow([tid, plate, conf])

print("✅ Results saved to final_license_plate_results.csv")