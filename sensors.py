import cv2
import mediapipe as mp
import time
import math
from threading import Thread

class WebcamStream:
    """
    Threaded webcam capture to ensure the main loop never blocks on I/O.
    Always holds the most recent frame.
    """
    def __init__(self, src=0, width=640, height=480):
        # cv2.CAP_DSHOW is required on Windows to avoid MSMF errors and reduce initialization latency
        self.stream = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Read first frame to ensure it's working
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        while True:
            if self.stopped:
                return
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

class HandTracker:
    def __init__(self, detection_con=0.6, track_con=0.6):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,         # Only track one hand for performance
            model_complexity=0,      # Fastest model
            min_detection_confidence=detection_con,
            min_tracking_confidence=track_con
        )
        
        # Tracking State
        self.prev_x, self.prev_y = 0, 0
        self.prev_time = time.time()
        
        # Adaptive Smoothing params
        self.alpha = 0.5 
        
    def is_palm_open(self, lm_list):
        """
        Heuristic to check if hand is open.
        Checks if tips of fingers (8, 12, 16, 20) are far from wrist (0)
        and spread out.
        """
        if not lm_list:
            return False
            
        # 1. Check if all fingers are extended (tipy < pipy usually for upright hand, 
        # but rotation matters. Better: Dist(Tip, Wrist) > Dist(Pip, Wrist))
        # Simple heuristic: Check distance of tips from wrist
        wrist = lm_list[0]
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        
        open_fingers = 0
        for i in range(4):
            tip = lm_list[tips[i]]
            pip = lm_list[pips[i]]
            
            # Simple check: Tip is further from wrist than PIP
            dist_tip = math.hypot(tip[1]-wrist[1], tip[2]-wrist[2])
            dist_pip = math.hypot(pip[1]-wrist[1], pip[2]-wrist[2])
            
            if dist_tip > dist_pip:
                open_fingers += 1
                
        return open_fingers == 4 # Thumb is tricky, ignoring for "Palm"

    def find_position(self, frame):
        """
        Processes frame and returns:
        cx, cy, velocity, is_palm_open
        """
        # Optimization: Pass by reference
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_rgb.flags.writeable = False
        
        results = self.hands.process(img_rgb)
        
        timestamp = time.time()
        dt = timestamp - self.prev_time
        if dt == 0: dt = 0.001
        
        lm_list_formatted = []
        is_open = False
        
        cx, cy, velocity = None, None, 0.0
        
        if results.multi_hand_landmarks:
            hand_lms = results.multi_hand_landmarks[0]
            h, w, c = frame.shape
            
            # Extract all landmarks for gesture logic
            for id, lm in enumerate(hand_lms.landmark):
                lm_list_formatted.append([id, lm.x, lm.y]) # storing normalized for logic or pixels?
                # logic above uses pixels or relative? Let's use pixels for consistency with drawing?
                # Logic above used hypot on x,y. Let's convert all to pixels for the helper.
            
            # Re-convert to list of [id, x, y] (pixels)
            pixel_lms = []
            for lm in hand_lms.landmark:
                pixel_lms.append([0, int(lm.x*w), int(lm.y*h)]) # ID not needed in index, just position
            
            # Index Finger Tip is ID 8
            raw_x, raw_y = pixel_lms[8][1], pixel_lms[8][2]
            
            # Check Gesture
            is_open = self.is_palm_open(pixel_lms)
            
            # --- Adaptive Smoothing (Copy from before) ---
            dist = math.hypot(raw_x - self.prev_x, raw_y - self.prev_y)
            if dist > 30: target_alpha = 0.8 
            else: target_alpha = 0.2
            
            self.alpha = target_alpha
            
            if self.prev_x == 0 and self.prev_y == 0:
                smooth_x, smooth_y = raw_x, raw_y
            else:
                smooth_x = self.alpha * raw_x + (1 - self.alpha) * self.prev_x
                smooth_y = self.alpha * raw_y + (1 - self.alpha) * self.prev_y
            
            move_dist = math.hypot(smooth_x - self.prev_x, smooth_y - self.prev_y)
            velocity = move_dist / dt 
            
            self.prev_x, self.prev_y = smooth_x, smooth_y
            
            cx, cy = int(smooth_x), int(smooth_y)
            
        self.prev_time = timestamp
        return cx, cy, velocity, is_open
