import cv2
import numpy as np
import threading

classes = ["Helipad"]
cap = cv2.VideoCapture(0)
net = cv2.dnn.readNetFromONNX("helipadorange.onnx")

frame = None
detections = None
lock = threading.Lock()

def capture_frames():
    global frame
    while True:
        ret, img = cap.read()
        if not ret:
            break
        with lock:
            frame = img.copy()

def detect_objects():
    global detections
    while True:
        with lock:
            if frame is None:
                continue
            blob = cv2.dnn.blobFromImage(frame, 1/255, (640, 640), (0, 0, 0), True, False)
        net.setInput(blob)
        detections = net.forward()[0]

def find_helipad_center(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1.2, 100, param1=100, param2=30, minRadius=30, maxRadius=200)

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            cv2.circle(frame, (x, y), r, (0, 255, 0), 4)
            cv2.rectangle(frame, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)
            return frame, (x, y)
    return frame, None

def display_frame():
    while True:
        with lock:
            if frame is None or detections is None:
                continue
            img, det = frame.copy(), detections.copy()

        boxes, confidences, class_ids = [], [], []
        img_w, img_h = img.shape[1], img.shape[0]
        x_scale, y_scale = img_w / 640, img_h / 640

        for row in det:
            confidence = row[4]
            if confidence > 0.2:
                scores = row[5:]
                class_id = np.argmax(scores)
                if scores[class_id] > 0.2:
                    confidences.append(confidence)
                    class_ids.append(class_id)
                    cx, cy, w, h = row[:4]
                    boxes.append([int((cx - w / 2) * x_scale), int((cy - h / 2) * y_scale), int(w * x_scale), int(h * y_scale)])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.2, 0.2)
        if len(indices) > 0:
            indices = indices.flatten()
            for i in indices:
                x, y, w, h = boxes[i]
                label = f"{classes[class_ids[i]]} {confidences[i]:.2f}"
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(img, label, (x, y - 2), cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 0, 255), 2)

        img, center = find_helipad_center(img)
        if center:
            print(f"Helipad center: {center}")

        cv2.imshow("Deteksi Objek", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break

if __name__ == "__main__":
    threads = [threading.Thread(target=func) for func in [capture_frames, detect_objects, display_frame]]
    for t in threads: t.start()
    for t in threads: t.join()

    cap.release()
    cv2.destroyAllWindows()
