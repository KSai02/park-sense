from flask import Flask, render_template, Response, jsonify, request, send_file, redirect, url_for, session, flash
import cv2
import numpy as np
import os
import threading
import queue
import time
import uuid
from datetime import datetime,timedelta
from database import db
import qrcode
from functools import wraps
from ultralytics import YOLO
from paddleocr import PaddleOCR
from collections import defaultdict, Counter
from io import BytesIO
from threading import Thread
from deep_sort_realtime.deepsort_tracker import DeepSort
from pyngrok import ngrok

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Model paths
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models')
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, 'yolov8', 'yolov8n.pt')
LICENSE_PLATE_MODEL_PATH = os.path.join(MODELS_DIR, 'license_plate', 'license_plate_detector.pt')

FRAME_QUEUE_SIZE = 1
JPEG_QUALITY = 80

# Initialize models
vehicle_model = YOLO(YOLO_MODEL_PATH)
plate_model = YOLO(LICENSE_PLATE_MODEL_PATH)
ocr = PaddleOCR(use_angle_cls=True, lang='en', det_model_dir=os.path.join(MODELS_DIR, 'license_plate_detector'), use_gpu=False, enable_mkldnn=True, cpu_threads=4)

# Initialize DeepSORT tracker
tracker = DeepSort(max_age=30, n_init=1)

# Shared state
frame_queue = queue.Queue(maxsize=FRAME_QUEUE_SIZE)
detection_queue = queue.Queue(maxsize=FRAME_QUEUE_SIZE)
shared_state = {'predictions': [], 'progress': {}, 'total_frames_scanned': 0, 'plate_ready_for_verification': None, 'all_predictions': []}
shared_state_lock = threading.Lock()
latest_frame = None
latest_frame_lock = threading.Lock()
active_registrations = {}
parking_records = {}
all_predictions = []  # Accumulate all predictions

# Add this global variable to keep track of plate text counts
plate_text_counter = {}

# Camera manager for frame capture
class CameraManager:
    def __init__(self):
        self.camera = cv2.VideoCapture(1)
        if not self.camera.isOpened():
            print("Camera 1 not available, trying camera 0...")
            self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise RuntimeError("Failed to open any camera")
        self.frame_count = 0
        self.fps = 0
        self.last_frame_time = time.time()
        self.lock = threading.Lock()
    def read(self):
        with self.lock:
            ret, frame = self.camera.read()
            if not ret:
                return False, None
            self.frame_count += 1
            now = time.time()
            if now - self.last_frame_time > 1.0:
                self.fps = self.frame_count / (now - self.last_frame_time)
                self.frame_count = 0
                self.last_frame_time = now
            return True, frame
    def release(self):
        with self.lock:
            if self.camera:
                self.camera.release()

camera_manager = CameraManager()

def enhance_frame(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    return sharpened

def generate_frames():
    global latest_frame, latest_frame_lock, shared_state, shared_state_lock
    while True:
        try:
            with latest_frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None
            if frame is None:
                time.sleep(0.01)
                continue
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Error in generate_frames: {str(e)}")
            time.sleep(0.01)
            continue

class DetectionState:
    def __init__(self):
        self.predictions = []
        self.plate_detections = {}
        self.frame_count = 0
        self.is_testing = False
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.FRAMES_BEFORE_QR = 10
        self.plate_history = {}
        self.plate_ready_for_verification = None
        self.all_predictions = []  # Accumulate all predictions
    def update_predictions(self, new_predictions):
        with self.lock:
            try:
                print(f"[DEBUG] update_predictions: called with {len(new_predictions)} predictions")
                self.frame_count += 1
                detected_keys = set()
                if new_predictions:
                    # db.bookings.update_many(
                    # {
                    #     "status": "booked",
                    #     "booking_time": {"$lt": datetime.utcnow() - timedelta(minutes=10)}
                    # },
                    # {"$set": {"status": "expired"}}
                    # )
                    self.predictions = new_predictions
                    # Add all new predictions to the global history
                    for pred in new_predictions:
                        pred_copy = pred.copy()
                        if 'track_id' in pred_copy:
                            del pred_copy['track_id']
                        self.all_predictions.append(pred_copy)
                    self.last_update = time.time()
                    for pred in new_predictions:
                        plate_box = pred.get('plate_box')
                        bbox = pred.get('bbox')
                        plate_text = pred.get('plate_text')
                        plate_conf = pred.get('plate_conf', 0)
                        now = time.time()
                        # Only track progress for plates
                        if plate_text:
                            key = plate_text.upper().strip()
                        else:
                            continue
                        detected_keys.add(key)
                        if key not in self.plate_history:
                            print(f"[DEBUG] update_predictions: New detection tracked: {key}")
                            self.plate_history[key] = {
                                'confidences': [plate_conf],
                                'max_conf': plate_conf,
                                'frames': 1,
                                'last_update': now,
                                'total': self.FRAMES_BEFORE_QR,
                                'verified': False,
                                'bbox': bbox,
                                'plate_box': plate_box,
                                'plate_text': plate_text,
                                'qr_generated': False,
                                'qr_path': None
                            }
                        else:
                            hist = self.plate_history[key]
                            hist['confidences'].append(plate_conf)
                            hist['max_conf'] = max(hist['max_conf'], plate_conf)
                            hist['frames'] = min(hist['frames'] + 1, self.FRAMES_BEFORE_QR)
                            hist['last_update'] = now
                            # Always update with latest detection data
                            hist['bbox'] = bbox
                            hist['plate_box'] = plate_box
                            hist['plate_text'] = plate_text
                            # Optionally, update plate_conf to latest
                            hist['plate_conf'] = plate_conf
                        # Generate QR if not already done and progress is 100%
                        hist = self.plate_history[key]
                    #     if (hist['frames'] >= self.FRAMES_BEFORE_QR and plate_conf > 0.5 and not hist['verified'] and plate_text):
                    #         print(f"[DEBUG] update_predictions: Plate {key} ready for verification!")
                    #         self.plate_ready_for_verification = key
    

                    #         hist['verified'] = True
                    #         if not hist['qr_generated']:
                    #             qr_io = generate_entry_qr(key, hist['max_conf'])
                    #             qr_filename = f"entry_qr_{key}_{int(time.time())}.png"
                    #             qr_path = os.path.join(os.path.dirname(__file__), 'static', qr_filename)
                    #             with open(qr_path, 'wb') as f:
                    #                 f.write(qr_io.getvalue())
                    #             hist['qr_generated'] = True
                    #             hist['qr_path'] = qr_path
                    #             print(f"[DEBUG] QR generated for {key} at {qr_path}")
                    # current_time = time.time()
                    # for key in list(self.plate_history.keys()):
                    #     if current_time - self.plate_history[key]['last_update'] > 30.0:
                    #         print(f"[DEBUG] update_predictions: Removing stale detection {key}")
                    #         del self.plate_history[key]
                        if (hist['frames'] >= self.FRAMES_BEFORE_QR and plate_conf > 0.5 and not hist['verified'] and plate_text):
                            key = plate_text.upper().strip()
                            self.plate_ready_for_verification = key
                            print(f"[DEBUG] update_predictions: Plate {key} ready for verification!")
    # Check: already parked? skip QR
                            already_parked = db.parking_records.find_one({
                                            "plate_number": key,
                                            "status": "active"
                                            })
                            if already_parked:
                                print(f"[INFO] Plate {key} already parked. Skipping.")
                                hist['verified'] = True
                                continue

    # Check: recently booked?
                            existing_booking = db.bookings.find_one({
                                                "plate_number": key,
                                                "status": "booked",
                                                "booking_time": {"$gte": datetime.now() - timedelta(minutes=10)}
                                                })
                            if existing_booking:
                                print(f"[INFO] Fastlane booking found for {key}")
                                hist['verified'] = True
                                self.plate_ready_for_verification = f"FASTLANE::{key}"
                                continue

    # Normal QR logic
                            
                            hist['verified'] = True
                            if not hist['qr_generated']:
                                qr_io = generate_entry_qr(key, hist['max_conf'])
                                qr_filename = f"entry_qr_{key}_{int(time.time())}.png"
                                qr_path = os.path.join(os.path.dirname(__file__), 'static', qr_filename)
                                with open(qr_path, 'wb') as f:
                                    f.write(qr_io.getvalue())
                                    hist['qr_generated'] = True
                                    hist['qr_path'] = qr_path
                                    print(f"[DEBUG] QR generated for {key} at {qr_path}")

                else:
                    self.predictions = []
            except Exception as e:
                print(f"[DEBUG] update_predictions: Exception: {str(e)}")
    def get_predictions(self):
        with self.lock:
            try:
                if time.time() - self.last_update > 5:
                    self.predictions = []
                # Only show progress for the most recent frame's predictions
                progress_data = {}
                for pred in self.predictions:
                    plate_box = pred.get('plate_box')
                    bbox = pred.get('bbox')
                    plate_text = pred.get('plate_text')
                    if plate_text:
                        key = plate_text.upper().strip()
                    elif plate_box is not None and bbox is not None:
                        key = f"PLATEBOX_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}"
                    else:
                        key = f"VEHICLE_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}"
                    hist = self.plate_history.get(key, None)
                    if hist:
                        progress_data[key] = {
                            'frames': hist['frames'],
                            'total_frames': hist.get('total', self.FRAMES_BEFORE_QR),
                            'progress': (hist['frames'] / hist.get('total', self.FRAMES_BEFORE_QR)) * 100,
                            'confidence': hist['max_conf']
                        }
                return {
                    'predictions': self.all_predictions,  # All predictions ever made
                    'progress': progress_data,            # Only progress for most recent frame
                    'total_frames_scanned': self.frame_count,
                    'plate_ready_for_verification': self.plate_ready_for_verification
                }
            except Exception as e:
                print(f"Error getting predictions: {str(e)}")
                return {'predictions': [], 'progress': {}, 'total_frames_scanned': self.frame_count, 'plate_ready_for_verification': None}

detection_state = DetectionState()

def process_frame(frame):
    global plate_text_counter
    try:
        frame_start = time.time()
        if frame is None:
            print("[DEBUG] process_frame: Received empty frame!")
            return
        VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck (COCO)
        try:
            vehicle_results = vehicle_model(frame, conf=0.5)
            print(f"[DEBUG] process_frame: vehicle_model returned {len(vehicle_results)} results")
        except Exception as e:
            print(f"[DEBUG] process_frame: vehicle_model error: {str(e)}")
            return
        current_predictions = []
        all_boxes = []
        all_scores = []
        all_classes = []
        for result in vehicle_results:
            try:
                boxes = result.boxes
                print(f"[DEBUG] process_frame: Found {len(boxes)} vehicle boxes")
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    if cls in VEHICLE_CLASSES:
                        all_boxes.append([x1, y1, x2, y2])
                        all_scores.append(conf)
                        all_classes.append(cls)
            except Exception as e:
                print(f"[DEBUG] process_frame: Error in vehicle box extraction: {str(e)}")
                continue
        print(f"[DEBUG] process_frame: {len(all_boxes)} boxes after YOLO, running DeepSORT")
        detections = []
        for i in range(len(all_boxes)):
            try:
                det = np.array(all_boxes[i] + [all_scores[i]], dtype=np.float32)
                if det.shape == (5,):
                    detections.append(det)
            except Exception as e:
                print(f"[DEBUG] process_frame: Error creating detection array: {str(e)}")
                continue
        print(f"[DEBUG] detections for DeepSORT: {detections}")
        detections_np = np.array(detections, dtype=np.float32)
        if detections_np.ndim == 1 and detections_np.size == 5:
            detections_np = detections_np.reshape(1, 5)
        elif detections_np.size == 0:
            detections_np = np.empty((0, 5), dtype=np.float32)
        try:
            tracks = tracker.update_tracks(detections_np, frame=frame)
            print(f"[DEBUG] process_frame: DeepSORT returned {len(tracks)} tracks")
        except Exception as e:
            print(f"[DEBUG] process_frame: DeepSORT tracking error: {str(e)}")
            tracks = []
        used_indices = set()
        current_predictions = []
        for i, track in enumerate(tracks):
            if not track.is_confirmed():
                continue
            start_pred = time.time()
            track_id = track.track_id
            det_idx = track.det_index if hasattr(track, 'det_index') else i
            used_indices.add(det_idx)
            x1, y1, x2, y2 = all_boxes[det_idx]
            conf = all_scores[det_idx]
            cls = all_classes[det_idx]
            vehicle_pred = {
                'bbox': [x1, y1, x2, y2],
                'plate_box': None,
                'plate_text': None,
                'confidence': conf,
                'plate_conf': None,
                'track_id': track_id,
                'timestamp': time.time()
            }
            # License plate detection and OCR
            if cls in VEHICLE_CLASSES and conf > 0.5:
                height = y2 - y1
                width = x2 - x1
                pad_x = int(width * 0.1)
                pad_y = int(height * 0.1)
                roi_x1 = max(0, x1 - pad_x)
                roi_y1 = max(0, y1 - pad_y)
                roi_x2 = min(frame.shape[1], x2 + pad_x)
                roi_y2 = min(frame.shape[0], y2 + pad_y)
                vehicle_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                if vehicle_roi.size > 0:
                    vehicle_roi = enhance_frame(vehicle_roi)
                    try:
                        plate_results = plate_model(vehicle_roi, conf=0.4)
                    except Exception as e:
                        print(f"[DEBUG] process_frame: plate_model error: {str(e)}")
                        current_predictions.append(vehicle_pred)
                        continue
                    best_plate_this_frame = None
                    best_conf_this_frame = 0
                    for plate_result in plate_results:
                        try:
                            plate_boxes = plate_result.boxes
                            for plate_box in plate_boxes:
                                px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                                pconf = float(plate_box.conf[0])
                                if pconf > best_conf_this_frame:
                                    best_conf_this_frame = pconf
                                    best_plate_this_frame = (px1, py1, px2, py2)
                        except Exception as e:
                            print(f"[DEBUG] process_frame: Error in plate box extraction: {str(e)}")
                            continue
                    if best_plate_this_frame:
                        px1, py1, px2, py2 = best_plate_this_frame
                        plate_roi = vehicle_roi[py1:py2, px1:px2]
                        plate_text = None
                        plate_conf = best_conf_this_frame
                        if plate_roi.size > 0 and ocr is not None:
                            ocr_start = time.time()
                            ocr_result = ocr.ocr(plate_roi, cls=True)
                            ocr_end = time.time()
                            print(f"[PROFILE] OCR for DeepSORT vehicle {i} took {ocr_end - ocr_start:.3f} seconds")
                            if ocr_result and ocr_result[0]:
                                for line in ocr_result[0]:
                                    box, (text, conf_ocr) = line
                                    text = ''.join(c for c in text if c.isalnum()).upper().strip()
                                    if len(text) >= 4:
                                        plate_text = text
                                        plate_conf = conf_ocr
                                        # Count occurrences of this plate text
                                        if plate_text not in plate_text_counter:
                                            plate_text_counter[plate_text] = 1
                                        else:
                                            plate_text_counter[plate_text] += 1
                                        # Trigger QR if count reaches 10
                                        if plate_text_counter[plate_text] == 10:
                                            print(f"[DEBUG] QR triggered for plate: {plate_text}")
                                            qr_io = generate_entry_qr(plate_text, plate_conf)
                                            qr_path = os.path.join(os.path.dirname(__file__), 'static', f'{plate_text}_entry_qr.png')
                                            with open(qr_path, 'wb') as f:
                                                f.write(qr_io.getvalue())
                                        break
                        vehicle_pred['plate_box'] = [px1 + roi_x1, py1 + roi_y1, px2 + roi_x1, py2 + roi_y1]
                        vehicle_pred['plate_text'] = plate_text
                        vehicle_pred['plate_conf'] = plate_conf if plate_text else best_conf_this_frame
            end_pred = time.time()
            print(f"[PROFILE] Prediction+OCR for DeepSORT vehicle {i} took {end_pred - start_pred:.3f} seconds")
            current_predictions.append(vehicle_pred)
        # Fallback: add YOLO boxes not used by DeepSORT as predictions (no track_id)
        for i in range(len(all_boxes)):
            if i not in used_indices:
                start_pred = time.time()
                x1, y1, x2, y2 = all_boxes[i]
                conf = all_scores[i]
                cls = all_classes[i]
                vehicle_pred = {
                    'bbox': [x1, y1, x2, y2],
                    'plate_box': None,
                    'plate_text': None,
                    'confidence': conf,
                    'plate_conf': None,
                    'track_id': None,
                    'timestamp': time.time()
                }
                # License plate detection and OCR for fallback
                if cls in VEHICLE_CLASSES and conf > 0.5:
                    height = y2 - y1
                    width = x2 - x1
                    pad_x = int(width * 0.1)
                    pad_y = int(height * 0.1)
                    roi_x1 = max(0, x1 - pad_x)
                    roi_y1 = max(0, y1 - pad_y)
                    roi_x2 = min(frame.shape[1], x2 + pad_x)
                    roi_y2 = min(frame.shape[0], y2 + pad_y)
                    vehicle_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                    if vehicle_roi.size > 0:
                        vehicle_roi = enhance_frame(vehicle_roi)
                        try:
                            plate_results = plate_model(vehicle_roi, conf=0.4)
                        except Exception as e:
                            print(f"[DEBUG] process_frame: plate_model error: {str(e)}")
                            current_predictions.append(vehicle_pred)
                            continue
                        best_plate_this_frame = None
                        best_conf_this_frame = 0
                        for plate_result in plate_results:
                            try:
                                plate_boxes = plate_result.boxes
                                for plate_box in plate_boxes:
                                    px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                                    pconf = float(plate_box.conf[0])
                                    if pconf > best_conf_this_frame:
                                        best_conf_this_frame = pconf
                                        best_plate_this_frame = (px1, py1, px2, py2)
                            except Exception as e:
                                print(f"[DEBUG] process_frame: Error in plate box extraction: {str(e)}")
                                continue
                        if best_plate_this_frame:
                            px1, py1, px2, py2 = best_plate_this_frame
                            plate_roi = vehicle_roi[py1:py2, px1:px2]
                            plate_text = None
                            plate_conf = best_conf_this_frame
                            if plate_roi.size > 0 and ocr is not None:
                                ocr_start = time.time()
                                ocr_result = ocr.ocr(plate_roi, cls=True)
                                ocr_end = time.time()
                                print(f"[PROFILE] OCR for fallback YOLO vehicle {i} took {ocr_end - ocr_start:.3f} seconds")
                                if ocr_result and ocr_result[0]:
                                    for line in ocr_result[0]:
                                        box, (text, conf_ocr) = line
                                        text = ''.join(c for c in text if c.isalnum()).upper().strip()
                                        if len(text) >= 4:
                                            plate_text = text
                                            plate_conf = conf_ocr
                                            # Count occurrences of this plate text
                                            if plate_text not in plate_text_counter:
                                                plate_text_counter[plate_text] = 1
                                            else:
                                                plate_text_counter[plate_text] += 1
                                            # Trigger QR if count reaches 10
                                            if plate_text_counter[plate_text] == 10:
                                                print(f"[DEBUG] QR triggered for plate: {plate_text}")
                                                qr_io = generate_entry_qr(plate_text, plate_conf)
                                                qr_path = os.path.join(os.path.dirname(__file__), 'static', f'{plate_text}_entry_qr.png')
                                                with open(qr_path, 'wb') as f:
                                                    f.write(qr_io.getvalue())
                                            break
                            vehicle_pred['plate_box'] = [px1 + roi_x1, py1 + roi_y1, px2 + roi_x1, py2 + roi_y1]
                            vehicle_pred['plate_text'] = plate_text
                            vehicle_pred['plate_conf'] = plate_conf if plate_text else best_conf_this_frame
                end_pred = time.time()
                print(f"[PROFILE] Prediction+OCR for fallback YOLO vehicle {i} took {end_pred - start_pred:.3f} seconds")
                current_predictions.append(vehicle_pred)
        print(f"[DEBUG] process_frame: Added {len(current_predictions)} predictions")
        # Filter predictions: only those with valid plate_box and plate_text, and only highest-confidence per plate_text
        plate_detections = [p for p in current_predictions if p['plate_box'] is not None and p['plate_text'] is not None]
        if plate_detections:
            best_by_plate = {}
            for pred in plate_detections:
                key = pred['plate_text']
                if key not in best_by_plate or (pred['plate_conf'] is not None and pred['plate_conf'] > best_by_plate[key].get('plate_conf', 0)):
                    best_by_plate[key] = pred
            filtered_predictions = list(best_by_plate.values())
        else:
            # If no plate detected, keep only the highest-confidence vehicle detection
            if current_predictions:
                best_vehicle = max(current_predictions, key=lambda p: p['confidence'])
                filtered_predictions = [best_vehicle]
            else:
                filtered_predictions = []
        print(f"[DEBUG] process_frame: Filtered to {len(filtered_predictions)} predictions")
        detection_state.update_predictions(filtered_predictions)
        frame_end = time.time()
        print(f"[PROFILE] Total process_frame time: {frame_end - frame_start:.3f} seconds")
    except Exception as e:
        print(f"[DEBUG] process_frame: Exception: {str(e)}")
        return

def capture_frames():
    global frame_queue, latest_frame, latest_frame_lock
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_frame, "Camera Not Available", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(test_frame, "Attempting to reconnect...", (150, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    while True:
        try:
            ret, frame = camera_manager.read()
            if not ret:
                try:
                    frame_queue.put(test_frame.copy(), timeout=0.1)
                except queue.Full:
                    pass
                time.sleep(1)
                continue
            with latest_frame_lock:
                global latest_frame
                latest_frame = frame.copy()
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put(frame, timeout=0.1)
        except Exception as e:
            time.sleep(0.1)
            continue

def detection_worker():
    while True:
        try:
            frame = frame_queue.get(timeout=0.1)
            preds = process_frame_multithreaded(frame)
            if detection_queue.full():
                try:
                    detection_queue.get_nowait()
                except queue.Empty:
                    pass
            detection_queue.put(preds, timeout=0.1)
        except queue.Empty:
            continue
        except Exception as e:
            continue

def prediction_poster():
    while True:
        try:
            preds = detection_queue.get(timeout=0.1)
            with shared_state_lock:
                shared_state['predictions'] = preds['predictions']
                shared_state['progress'] = preds['progress']
                shared_state['total_frames_scanned'] = preds['total_frames_scanned']
                shared_state['plate_ready_for_verification'] = preds['plate_ready_for_verification']
        except queue.Empty:
            continue
        except Exception as e:
            continue

def process_frame_multithreaded(frame):
    process_frame(frame)
    preds = detection_state.get_predictions()
    return preds

# Helper functions
# (assign_parking_slot, generate_entry_qr, generate_parking_qr)
def assign_parking_slot():
    try:
        available_slot = db.slots.find_one_and_update(
            {'status': 'empty'},
            {'$set': {'status': 'reserved', 'last_updated': datetime.now()}},
            sort=[('space_id', 1)]
        )
        if available_slot:
            return available_slot['space_id'],available_slot['lot_id']
        return None
    except Exception as e:
        print(f"Error assigning parking slot: {str(e)}")
        return None


def generate_entry_qr(plate_number, confidence):
    registration_id = str(uuid.uuid4())
    slot,lot_id=assign_parking_slot()
    active_registrations[registration_id] = {
        'plate_number': plate_number,
        'confidence': confidence,
        'timestamp': datetime.now().isoformat(),
        'slot':slot,
        'lot_id':lot_id
    }
    registration_url = f'{NGROK_URL}/register/{registration_id}'
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(registration_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

def generate_parking_qr(parking_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'{NGROK_URL}/exit/validate_exit/{parking_id}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

# Start threads for frame capture, detection, and prediction posting
frame_capture_thread = Thread(target=capture_frames, daemon=True)
detection_thread = Thread(target=detection_worker, daemon=True)
prediction_post_thread = Thread(target=prediction_poster, daemon=True)
frame_capture_thread.start()
detection_thread.start()
prediction_post_thread.start()

# --- User routes ---
@app.route('/')
def index():
    return render_template('entry_screen.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/predictions')
def get_predictions():
    try:
        db.bookings.update_many(
            {
                "status": "booked",
                "booking_time": {"$lt": datetime.utcnow() - timedelta(minutes=10)}
            },
            {"$set": {"status": "expired"}}
        )
    except Exception as e:
        print(f"[WARNING] Failed booking expiry check: {e}")
    with shared_state_lock:
        response_data = {
            'predictions': shared_state['predictions'],
            'progress': shared_state['progress'],
            'total_frames_scanned': shared_state['total_frames_scanned'],
            'plate_ready_for_verification': shared_state['plate_ready_for_verification']
        }
    return jsonify(response_data)

@app.route('/get_exit_qr_form')
def get_exit_qr_form():
    return render_template('exit_qr_form.html')


@app.route('/fastlane/<plate>')
def fastlane_entry(plate):
    booking = db.bookings.find_one({
        "plate_number": plate.upper(),
        "status": "booked",
        "booking_time": {"$gte": datetime.utcnow() - timedelta(minutes=10)}
    })
    if not booking:
        return redirect(url_for('index'))

    return render_template(
        'fastlane_entry.html',
        plate_number=plate.upper(),
        slot_number=booking['slot_no'],
        lot_id=booking.get('lot_id', 'N/A')
    )

@app.route('/clear_plate/<plate>')
def clear_plate(plate):
    plate = plate.upper().strip()
    with detection_state.lock:
        # Remove plate from history and verification state
        if plate in detection_state.plate_history:
            del detection_state.plate_history[plate]
        if detection_state.plate_ready_for_verification == plate:
            detection_state.plate_ready_for_verification = None
    return jsonify({"cleared": True})


@app.route('/register/<registration_id>')
def registration_page(registration_id):
    if registration_id not in active_registrations:
        return "Invalid registration link", 404
    reg_data = active_registrations[registration_id]
    slot=reg_data['slot']
    lot=reg_data['lot_id']
    return render_template('register.html',slot=slot,lot=lot, plate_number=reg_data['plate_number'], registration_id=registration_id)

# @app.route('/submit_registration', methods=['POST'])
# def submit_registration():
#     reg_id = request.form['registration_id']
#     if reg_id not in active_registrations:
#         return "Invalid registration", 404
#     reg_data = active_registrations[reg_id]
#     slot = assign_parking_s
#     try:
#         if slot is not None:
#             parking_id = str(uuid.uuid4())
#             parking_record = {
#                 'parking_id': parking_id,
#                 'slot': slot,
#                 'plate_number': reg_data['plate_number'],
#                 'name': request.form['name'],
#                 'phone': request.form['phone'],
#                 'entry_time': datetime.now(),
#                 'status': 'active',
#                 'registration_id': reg_id
#             }
#             db.parking_records.insert_one(parking_record)
#             db.parking_slots.update_one({'space_id': slot}, {'$set': {'status': 'occupied', 'current_vehicle': reg_data['plate_number'], 'last_updated': datetime.now()}})
#             del active_registrations[reg_id]
#             # Reset detection state for this registration
#             detection_state.plate_ready_for_verification = None
#             detection_state.predictions = []
#             detection_state.plate_history = {}
#             # Generate exit QR code and save to static
#             qr_io = generate_parking_qr(parking_id)
#             static_dir = os.path.join(os.path.dirname(__file__), 'static')
#             if not os.path.exists(static_dir):
#                 os.makedirs(static_dir)
#             qr_filename = f'exit_qr_{parking_id}.png'
#             qr_path = os.path.join(static_dir, qr_filename)
#             with open(qr_path, 'wb') as f:
#                 f.write(qr_io.getvalue())
#             return render_template('parking_assigned.html', slot_number=slot, parking_id=parking_id, exit_qr_filename=qr_filename)
#         else:
#             del active_registrations[reg_id]
#             return render_template('parking_assigned.html', slot_number=None, parking_id=None, no_slots=True)
#     except Exception as e:
#         print(f"Error in registration: {str(e)}")
#         if slot:
#             db.parking_slots.update_one({'space_id': slot}, {'$set': {'status': 'empty', 'current_vehicle': None}})
#         return "Registration failed", 500

# @app.route('/submit_registration', methods=['POST'])
# def submit_registration():
#     reg_id = request.form['registration_id']
#     if reg_id not in active_registrations:
#         return "Invalid registration", 404
#     reg_data = active_registrations[reg_id]
#     slot = reg_data.get('slot')  # Use the pre-assigned slot!
#     try:
#         if slot is not None:
#             parking_id = str(uuid.uuid4())
#             parking_record = {
#                 'parking_id': parking_id,
#                 'slot': slot,
#                 'plate_number': reg_data['plate_number'],
#                 'name': request.form['name'],
#                 'phone': request.form['phone'],
#                 'entry_time': datetime.now(),
#                 'status': 'active',
#                 'registration_id': reg_id
#             }
#             db.parking_records.insert_one(parking_record)
#             # Mark the slot as occupied in the DB
#             db.parking_slots.update_one(
#                 {'space_id': slot},
#                 {'$set': {'status': 'occupied', 'current_vehicle': reg_data['plate_number'], 'last_updated': datetime.now()}}
#             )
#             # Clean up registration (slot now officially reserved)
#             del active_registrations[reg_id]
#             # Reset detection state
#             detection_state.plate_ready_for_verification = None
#             detection_state.predictions = []
#             detection_state.plate_history = {}
#             # Generate exit QR code and save to static
#             qr_io = generate_parking_qr(parking_id)
#             static_dir = os.path.join(os.path.dirname(__file__), 'static')
#             if not os.path.exists(static_dir):
#                 os.makedirs(static_dir)
#             qr_filename = f'exit_qr_{parking_id}.png'
#             qr_path = os.path.join(static_dir, qr_filename)
#             with open(qr_path, 'wb') as f:
#                 f.write(qr_io.getvalue())
#             return render_template(
#                 'parking_assigned.html',
#                 slot_number=slot,
#                 parking_id=parking_id,
#                 exit_qr_filename=qr_filename,
#                 no_slots=False
#             )
#         else:
#             # No slot was assigned (should not happen under normal flow)
#             del active_registrations[reg_id]
#             return render_template(
#                 'parking_assigned.html',
#                 slot_number=None,
#                 parking_id=None,
#                 no_slots=True
#             )
#     except Exception as e:
#         print(f"Error in registration: {str(e)}")
#         # Roll back slot reservation if error happened
#         if slot:
#             db.parking_slots.update_one({'space_id': slot}, {'$set': {'status': 'empty', 'current_vehicle': None}})
#         return "Registration failed", 500


@app.route('/submit_registration', methods=['POST'])
def submit_registration():
    reg_id = request.form.get('registration_id')
    print("Received registration_id:", reg_id)
    name = request.form.get('name')
    phone = request.form.get('phone')
    print("Name:", name, "Phone:", phone)
    if reg_id not in active_registrations:
        print("Invalid registration_id")
        return "Invalid registration", 404
    reg_data = active_registrations[reg_id]
    slot = reg_data.get('slot')
    lot_id=reg_data.get('lot_id')
    try:
        if slot is not None:
            parking_id = str(uuid.uuid4())
            parking_record = {
                'parking_id': parking_id,
                'slot': slot,
                'plate_number': reg_data['plate_number'],
                'lot':lot_id,
                'name': name,
                'phone': phone,
                'entry_time': datetime.now(),
                'status': 'active',
                'registration_id': reg_id
            }
            print("Inserting parking record:", parking_record)
            db.parking_records.insert_one(parking_record)
            db.slots.update_one(
                {'space_id': slot, 'lot_id':lot_id},
                {'$set': {'status': 'occupied', 'current_vehicle': reg_data['plate_number'], 'last_updated': datetime.now()}}
            )
            # Update in-memory parking_records dict
            parking_records[parking_id] = parking_record
            del active_registrations[reg_id]
            detection_state.plate_ready_for_verification = None
            detection_state.predictions = []
            detection_state.plate_history = {}
            qr_io = generate_parking_qr(parking_id)
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            if not os.path.exists(static_dir):
                os.makedirs(static_dir)
            qr_filename = f'exit_qr_{parking_id}.png'
            qr_path = os.path.join(static_dir, qr_filename)
            with open(qr_path, 'wb') as f:
                f.write(qr_io.getvalue())
            return render_template(
                'parking_assigned.html',
                slot_number=slot,
                lot_id=lot_id,
                parking_id=parking_id,
                exit_qr_filename=qr_filename,
                no_slots=False
            )
        else:
            del active_registrations[reg_id]
            return render_template(
                'parking_assigned.html',
                slot_number=None,
                parking_id=None,
                no_slots=True
            )
    except Exception as e:
        print(f"Error in registration: {str(e)}")
        if slot:
            db.slots.update_one({'space_id': slot,'lot_id':lot_id}, {'$set': {'status': 'empty', 'current_vehicle': None}})
        return "Registration failed", 500
@app.route('/get_exit_qr/<qr_filename>')
def get_exit_qr(qr_filename):
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    qr_path = os.path.join(static_dir, qr_filename)
    if not os.path.exists(qr_path):
        return "QR code not found", 404
    return send_file(qr_path, mimetype='image/png')


@app.route('/exit')
def exit():
    return render_template('qr_scan.html')


@app.route('/get_exit_qr_online', methods=['POST'])
def get_exit_qr_online():
    plate = request.form['plate'].upper().strip()
    phone = request.form['phone'].strip()

    # Look up an active parking session
    record = db.parking_records.find_one({
        "plate_number": plate,
        "status": "active"
    })

    if not record:
        flash("No active parking session found.")
        return redirect(url_for('get_exit_qr_form'))

    # Validate phone number
    booking = db.bookings.find_one({
        "plate_number": plate,
        "phone": phone
    })

    if not booking:
        flash("Invalid phone number or plate.")
        return redirect(url_for('get_exit_qr_form'))

    # Generate exit QR if not already
    parking_id = record['parking_id']
    qr_filename = f'exit_qr_{parking_id}.png'
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    qr_path = os.path.join(static_dir, qr_filename)

    if not os.path.exists(qr_path):
        qr_io = generate_parking_qr(parking_id)
        with open(qr_path, 'wb') as f:
            f.write(qr_io.getvalue())

    return render_template('show_exit_qr.html', plate=plate, qr_filename=qr_filename)



# @app.route('/get_parking_qr/<parking_id>')
# def get_parking_qr(parking_id):
#     if parking_id not in parking_records:
#         return "Invalid parking ID", 404
#     qr_io = generate_parking_qr(parking_id)
#     return send_file(qr_io, mimetype='image/png')
#     @app.route('/get_parking_qr/<parking_id>')
def get_parking_qr(parking_id):
    record = db.parking_records.find_one({'parking_id': parking_id})
    if not record:
        return "Invalid parking ID", 404
    qr_io = generate_parking_qr(parking_id)
    return send_file(qr_io, mimetype='image/png')

@app.route('/exit/validate_exit/<parking_id>')
def validate_exit(parking_id):
    try:
        # Fetch the parking record
        record = db.parking_records.find_one({'parking_id': parking_id})
        if not record:
            return "Invalid parking ID", 404

        entry_time = record['entry_time']
        duration = datetime.now() - entry_time
        exit_time = datetime.now()

        # Update the parking record with exit time and status
        db.parking_records.update_one(
            {'parking_id': parking_id},
            {
                '$set': {
                    'exit_time': exit_time,
                    'status': 'exited'
                }
            }
        )

        # Free the associated slot
        if 'slot' in record:
            db.slots.update_one(
                {'space_id': record['slot'] , 'lot_id':record['lot']},
                {'$set': {
                    'status': 'empty',
                    'current_vehicle': None,
                    'last_updated': datetime.now()
                }}
            )

        # Update the record object to reflect changes (for rendering)
        record['exit_time'] = exit_time
        record['status'] = 'exited'

        return render_template('exit_validation.html', record=record, duration=duration)

    except Exception as e:
        print(f"Error validating exit: {str(e)}")
        return "Error validating exit", 500


@app.route('/test_detection')
def run_detection_test():
    # ... (copy logic from app.py)
    pass

@app.route('/detection_result')
def detection_result():
    plate = request.args.get('plate')
    ##
    if plate and plate.startswith("FASTLANE::"):
        clean_plate = plate.split("::")[1]
        return redirect(url_for('fastlane_entry', plate=clean_plate))
    if (
        not plate or
        detection_state.plate_ready_for_verification is None or
        plate.upper().strip() != detection_state.plate_ready_for_verification
    ):
        return redirect(url_for('rescan'))
    ##
    hist = detection_state.plate_history.get(plate.upper().strip()) if plate else None
    confidence = hist['max_conf'] if hist else 0
    # Find the registration QR code file if it was generated
    qr_path = None
    if hist and hist.get('qr_generated') and hist.get('qr_path'):
        # Get only the filename part for url_for
        qr_filename = os.path.basename(hist['qr_path'])
        qr_path = url_for('static', filename=qr_filename)
    return render_template('detection_result.html',
                           plate_number=plate,
                           confidence=confidence,
                           qr_path=qr_path)

@app.route('/rescan')
def rescan():
    # Optionally, clear any session or detection state if needed
    # For now, just redirect to index to trigger a new scan
    detection_state.plate_ready_for_verification = None
    detection_state.predictions = []
    detection_state.plate_history = {}
    with shared_state_lock:
        shared_state['predictions'] = []
        shared_state['progress'] = {}
        shared_state['total_frames_scanned'] = 0
        shared_state['plate_ready_for_verification'] = None
    return redirect(url_for('index'))

if __name__ == '__main__':
    ngrok.set_auth_token("") # Replace <YOUR_AUTHTOKEN> with your actual token
    NGROK_URL = ngrok.connect(5000).public_url
    print(f" * Public URL: {NGROK_URL}")
    app.run()
    #app.run(host='0.0.0.0', port=5000) 
