import math
import mediapipe as mp
import cv2

class PoseEngine:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        # We use a static image mode because we receive independent frames
        # Model complexity 0 is the lightest model (BlazePose Lite) for speed
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )

    def _calculate_angle(self, p1, p2, p3):
        """
        Calculate the angle between three points (p1, p2, p3) where p2 is the vertex.
        Points are (x, y).
        """
        radians = math.atan2(p3[1] - p2[1], p3[0] - p2[0]) - \
                  math.atan2(p1[1] - p2[1], p1[0] - p2[0])
        angle = abs(radians * 180.0 / math.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle

    def analyze_pose(self, rgb_frame):
        """
        Analyzes the pose in the given RGB frame and returns a posture suspicion probability.
        
        Args:
            rgb_frame (np.ndarray): The RGB image decoded by OpenCV.
            
        Returns:
            float: Suspicion probability [0, 1] based on anomalous posture (e.g. falling).
        """
        results = self.pose.process(rgb_frame)
        
        # If no pose is detected, we abstain from adding suspicion
        if not results.pose_landmarks:
            return 0.5 

        landmarks = results.pose_landmarks.landmark
        
        # Extract necessary landmarks for fall detection
        # We look at the angle between Shoulder, Hip, and Ankle to detect if someone is horizontal
        try:
            left_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                             landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            left_hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x,
                        landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
            left_ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                          landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            
            # Angle of the torso/leg line relative to the ground
            # A standing person has their shoulder vertically above their hip
            dx = abs(left_shoulder[0] - left_ankle[0])
            dy = abs(left_shoulder[1] - left_ankle[1])
            
            # If dy is very small compared to dx, the person is horizontal (falling/fallen)
            if dx > (dy * 1.5):
                # Highly suspicious (horizontal posture)
                return 0.85
                
            # Otherwise, normal standing/walking posture
            return 0.2
            
        except Exception as e:
            # Fallback if landmarks are missing or out of bounds
            return 0.5
