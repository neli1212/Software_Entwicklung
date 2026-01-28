import cv2
import os
from PIL import Image

class MediaProcessor:
    def __init__(self):
        # Supported formats
        self.img_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        self.vid_exts = (".mp4", ".avi", ".mkv", ".mov")

    def collect_all_media(self, paths):
        """
        Takes the mixed list from the UI and returns a list of 
        dictionaries: [{'path': '...', 'type': 'image' or 'video'}]
        """
        final_list = []
        for p in paths:
            if os.path.isdir(p):
                # Search inside folder
                for root, dirs, files in os.walk(p):
                    for f in files:
                        f_path = os.path.join(root, f)
                        if f.lower().endswith(self.img_exts):
                            final_list.append({'path': f_path, 'type': 'image'})
                        elif f.lower().endswith(self.vid_exts):
                            final_list.append({'path': f_path, 'type': 'video'})
            
            elif os.path.isfile(p):
                if p.lower().endswith(self.img_exts):
                    final_list.append({'path': p, 'type': 'image'})
                elif p.lower().endswith(self.vid_exts):
                    final_list.append({'path': p, 'type': 'video'})
        
        return final_list

    def extract_video_frames(self, video_path, interval_sec=1.0):
        """
        Generator that yields (PIL_Image, timestamp_string)
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: return

        frame_interval = int(max(1, fps * interval_sec))
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            if frame_idx % frame_interval == 0:
                # Convert BGR (OpenCV) to RGB (PIL/AI)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                
                # Calculate timestamp
                seconds = int(frame_idx / fps)
                timestamp = f"{seconds // 60}:{seconds % 60:02d}"
                
                yield pil_img, timestamp
            
            frame_idx += 1
        cap.release()