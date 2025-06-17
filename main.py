
import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import tempfile
import os
from PIL import Image

# Streamlit UI
st.title("🏃‍♂️ Vertical Jump Height Measurement")
uploaded_file = st.file_uploader("Upload a Video", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Save uploaded video to a temp file
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())

    # Setup Mediapipe
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(tfile.name)

    # Jump analysis variables
    INITIAL_FRAMES = 30
    initial_hip_y = None
    initial_frame_count = 0
    baseline_queue = deque(maxlen=INITIAL_FRAMES)
    jumping = False
    min_hip_y = float('inf')
    max_hip_y = float('-inf')
    jump_height = 0
    conversion_factor = None
    CALIBRATION_HEIGHT = 170  

    FRAME_WINDOW = st.image([])

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        image = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]

            hip_mid_x = int((left_hip.x + right_hip.x) * image.shape[1] / 2)
            hip_mid_y = int((left_hip.y + right_hip.y) * image.shape[0] / 2)

            if initial_frame_count < INITIAL_FRAMES:
                baseline_queue.append(hip_mid_y)
                initial_frame_count += 1

                if initial_frame_count == INITIAL_FRAMES:
                    initial_hip_y = np.mean(baseline_queue)
                    head_y = int(landmarks[mp_pose.PoseLandmark.NOSE.value].y * image.shape[0])
                    heel_y = int(max(
                        landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y,
                        landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].y
                    ) * image.shape[0])
                    body_height_pixels = abs(head_y - heel_y)
                    conversion_factor = CALIBRATION_HEIGHT / body_height_pixels

            elif initial_hip_y is not None:
                if not jumping and hip_mid_y < initial_hip_y - 15:
                    jumping = True
                    min_hip_y = hip_mid_y
                    max_hip_y = hip_mid_y

                if jumping:
                    min_hip_y = min(min_hip_y, hip_mid_y)
                    max_hip_y = max(max_hip_y, hip_mid_y)

                    if hip_mid_y > initial_hip_y - 5:
                        jumping = False
                        jump_height_pixels = initial_hip_y - min_hip_y
                        if conversion_factor:
                            jump_height = jump_height_pixels * conversion_factor
                        else:
                            jump_height = jump_height_pixels
                        min_hip_y = float('inf')
                        max_hip_y = float('-inf')

            # Drawing
            cv2.circle(image, (hip_mid_x, hip_mid_y), 8, (0, 150, 255), -1)
            if initial_hip_y is not None:
                cv2.line(image, (0, int(initial_hip_y)), (image.shape[1], int(initial_hip_y)), (100, 255, 100), 2)

            if jumping:
                cv2.line(image, (hip_mid_x, int(initial_hip_y)),
                         (hip_mid_x, min_hip_y), (255, 100, 0), 3)
                current_height = initial_hip_y - hip_mid_y
                display_height = current_height * conversion_factor if conversion_factor else current_height
                cv2.putText(image, f"Current: {display_height:.1f} {'cm' if conversion_factor else 'px'}",
                            (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 150), 2)

        # Display final jump height
        cv2.putText(image, f"Jump Height: {jump_height:.1f} {'cm' if conversion_factor else 'px'}",
                    (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 220, 255), 2)

        # Calibration or Status message
        status = "Calibrating..." if initial_frame_count < INITIAL_FRAMES else \
                 "Jump!" if jumping else "Ready..."
        cv2.putText(image, status, (10, image.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 200), 2)

        if initial_frame_count < INITIAL_FRAMES:
            cv2.rectangle(image, (50, 50), (image.shape[1]-50, image.shape[0]-50),
                          (30, 150, 255), 3)
            cv2.putText(image, "Stand in this area", (image.shape[1]//2-150, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 150, 255), 2)

        # Display the frame in Streamlit
        FRAME_WINDOW.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    cap.release()
    pose.close()
   
