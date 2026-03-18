import cv2
import os
from PIL import Image
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".JPG", ".JPEG")
VID_EXTS = (".mp4", ".avi", ".mkv", ".mov")

def collect_all_media(paths):
    """
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

