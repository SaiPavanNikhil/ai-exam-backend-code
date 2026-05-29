import cv2
import mediapipe as mp

# Initialize MediaPipe
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

# Start webcam
cap = cv2.VideoCapture(0)

with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:

    while cap.isOpened():
        success, frame = cap.read()

        if not success:
            break

        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = face_detection.process(rgb_frame)

        # Draw bounding boxes
        if results.detections:
            for detection in results.detections:
                mp_drawing.draw_detection(frame, detection)

        # Show video
        cv2.imshow('Face Detection', frame)

        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()