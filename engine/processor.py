import cv2
import os
from PIL import Image
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".JPG", ".JPEG")
VID_EXTS = (".mp4", ".avi", ".mkv", ".mov")

def collect_all_media(paths):
    """
    Stand-alone function to scan paths for media files.
    Takes a list of paths and returns a list of absolute file paths.
    """
    final_list = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                for f in files:
                    if f.lower().endswith(IMG_EXTS) or f.lower().endswith(VID_EXTS):
                        final_list.append(os.path.join(root, f))
        elif os.path.isfile(p):
            if p.lower().endswith(IMG_EXTS) or p.lower().endswith(VID_EXTS):
                final_list.append(p)
    return list(set(final_list)) 

class MediaProcessor:
    def __init__(self):
        self.img_exts = IMG_EXTS
        self.vid_exts = VID_EXTS

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
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                seconds = int(frame_idx / fps)
                timestamp = f"{seconds // 60}:{seconds % 60:02d}"
                yield pil_img, timestamp
            
            frame_idx += 1
        cap.release()