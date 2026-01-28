import torch, cv2, os
import torch.nn.functional as F
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForImageTextRetrieval

# Global cache to avoid reloading models on every scan
_GLOBAL_ENGINE = {"processor": None, "model_gen": None, "model_ret": None}

def get_engine(device):
    if _GLOBAL_ENGINE["processor"] is None:
        print("🚀 [AI] LOADING ENGINES (PROMPTING + VECTOR SEARCH)...")
        _GLOBAL_ENGINE["processor"] = BlipProcessor.from_pretrained("Salesforce/blip-itm-base-coco")
        _GLOBAL_ENGINE["model_gen"] = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)
        _GLOBAL_ENGINE["model_ret"] = BlipForImageTextRetrieval.from_pretrained("Salesforce/blip-itm-base-coco").to(device)
        print(f"✅ [AI] ENGINES READY ON {device.upper()}")
    return _GLOBAL_ENGINE["processor"], _GLOBAL_ENGINE["model_gen"], _GLOBAL_ENGINE["model_ret"]

class AIWorker(QThread):
    progress_update = Signal(int, str)
    result_found = Signal(dict)
    finished = Signal()

    def __init__(self, query_text, query_img_path, target_paths):
        super().__init__()
        self.query_text = query_text
        self.query_img_path = query_img_path
        self.target_paths = target_paths
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def run(self):
        try:
            proc, model_gen, model_ret = get_engine(self.device)
            final_query_text = self.query_text
            query_vec = None

            # --- 1. PROMPTING & FEATURE EXTRACTION ---
            if self.query_img_path:
                img = Image.open(self.query_img_path).convert('RGB')
                inputs = proc(images=img, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    # Generate caption for UI search bar (Automatic Prompting)
                    out = model_gen.generate(**inputs, max_new_tokens=30)
                    final_query_text = proc.decode(out[0], skip_special_tokens=True)
                    self.progress_update.emit(100, final_query_text)
                    
                    # Extract the search vector for 0.7 score logic
                    query_vec = model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]
                    query_vec = F.normalize(query_vec, p=2, dim=-1)

            # Exit if no targets are selected
            if not self.target_paths: return

            # --- 2. GLOBAL SEARCH ---
            for i, path in enumerate(self.target_paths):
                self.progress_update.emit(int((i/len(self.target_paths))*99), os.path.basename(path))
                
                if path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    self.process_vid(path, model_gen, model_ret, proc, query_vec)
                else:
                    self.process_img(path, model_gen, model_ret, proc, query_vec)

        except Exception as e:
            print(f"❌ [AI ERROR]: {e}")
        finally:
            self.finished.emit()

    def process_img(self, path, model_gen, model_ret, proc, query_vec):
        try:
            img = Image.open(path).convert('RGB')
            inputs = proc(images=img, return_tensors="pt").to(self.device)
            with torch.no_grad():
                # Extract image features
                target_vec = model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]
                target_vec = F.normalize(target_vec, p=2, dim=-1)
                
                # COSINE SIMILARITY (The 0.7 score fix)
                score = torch.nn.functional.cosine_similarity(query_vec, target_vec).item()

                out = model_gen.generate(pixel_values=inputs.pixel_values, max_new_tokens=30)
                cap = proc.decode(out[0], skip_special_tokens=True)
                self.result_found.emit({'path': path, 'score': score, 'caption': cap})
        except: pass

    def process_vid(self, path, model_gen, model_ret, proc, query_vec):
        cap_vid = cv2.VideoCapture(path)
        fps = cap_vid.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap_vid.get(cv2.CAP_PROP_FRAME_COUNT))
        
        best_score = -1.0
        best_data = None

        for f_idx in range(0, total, int(max(1, fps))):
            cap_vid.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap_vid.read()
            if not ret: break
            
            pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            inputs = proc(images=pil, return_tensors="pt").to(self.device)
            with torch.no_grad():
                # Extract frame features
                frame_vec = model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]
                frame_vec = F.normalize(frame_vec, p=2, dim=-1)
                
                # Compare features
                score = torch.nn.functional.cosine_similarity(query_vec, frame_vec).item()
                
                # Keep only the absolute best match for this video
                if score > best_score:
                    best_score = score
                    out = model_gen.generate(pixel_values=inputs.pixel_values, max_new_tokens=25)
                    best_data = {
                        'path': path, 'score': score, 
                        'caption': proc.decode(out[0], skip_special_tokens=True),
                        'timestamp': f"{int(f_idx/fps//60)}:{int(f_idx/fps%60):02d}"
                    }
        
        if best_data:
            self.result_found.emit(best_data)
        cap_vid.release()