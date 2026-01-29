import torch, cv2, os, re, threading
import torch.nn.functional as F
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForImageTextRetrieval

_GLOBAL_ENGINE = {"processor": None, "model_gen": None, "model_ret": None}
_ENGINE_LOCK = threading.Lock() 

MODEL_PATH = os.path.join(os.getcwd(), "ai_models")

def get_engine_safe(device_string):
    """Thread-safe global loader for the BLIP models."""
    global _GLOBAL_ENGINE
    with _ENGINE_LOCK: 
        if _GLOBAL_ENGINE["processor"] is None:
            print(f" [AI] LOADING ENGINES FROM: {MODEL_PATH}")
            dev = torch.device(device_string)
            _GLOBAL_ENGINE["processor"] = BlipProcessor.from_pretrained("Salesforce/blip-itm-base-coco", cache_dir=MODEL_PATH)
            _GLOBAL_ENGINE["model_gen"] = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir=MODEL_PATH).to(dev)
            _GLOBAL_ENGINE["model_ret"] = BlipForImageTextRetrieval.from_pretrained("Salesforce/blip-itm-base-coco", cache_dir=MODEL_PATH).to(dev)
            
            print(f"[AI] ENGINES READY ON {str(dev).upper()}")
    return _GLOBAL_ENGINE["processor"], _GLOBAL_ENGINE["model_gen"], _GLOBAL_ENGINE["model_ret"]

class ModelLoader(QThread):
    finished = Signal()
    def __init__(self):
        super().__init__()
        self.target_dev = "cuda" if torch.cuda.is_available() else "cpu"

    def run(self):
        try:
            get_engine_safe(self.target_dev)
        except Exception as e:
            print(f"[LOADER ERROR]: {e}")
        finally:
            self.finished.emit()

class AIWorker(QThread):
    progress_update = Signal(int, str)
    result_found = Signal(dict)
    finished = Signal()

    def __init__(self, query_text, query_img_path, target_paths, settings=None):
        super().__init__()
        self.query_text = query_text
        self.query_img_path = query_img_path
        self.target_paths = target_paths
        self.settings = settings if settings else {}
        self.mode = self.settings.get('mode', 'keyword')
        self.worker_device_str = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.query_words = []
        self.query_text_vec = None
        self.visual_query_vec = None

    def get_clean_words(self, text):
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'in', 'on', 'at', 'of', 'and', 'or', 'but', 'with', 'to', 'for', 'from', 'by', 'it', 'this', 'that', 'these', 'those', 'there'}
        raw = re.findall(r'\w+', text.lower())
        return [w for w in raw if w not in stopwords]

    def calculate_strict_keyword_score(self, target_caption, visual_score):
        if not self.query_words: return visual_score
        target_words_set = set(self.get_clean_words(target_caption))
        matches = sum(1 for w in self.query_words if w in target_words_set)
        total = len(self.query_words)
        if total == 0: return visual_score
        text_score = matches / total
        if text_score >= 1.0: return 1.0
        return (text_score * 0.9) + (visual_score * 0.1) if text_score > 0.5 else text_score * 0.5

    def calculate_vector_score(self, target_caption, target_visual_vec, proc, model_ret, device):
        inputs = proc(text=target_caption, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            text_outputs = model_ret.text_encoder(**inputs)
            target_cap_vec = model_ret.text_proj(text_outputs.last_hidden_state[:, 0, :])
            target_cap_vec = F.normalize(target_cap_vec, p=2, dim=-1)
        text_sim = F.cosine_similarity(self.query_text_vec, target_cap_vec).item() if self.query_text_vec is not None else 0.0
        visual_sim = F.cosine_similarity(self.visual_query_vec, target_visual_vec).item()
        final = (text_sim * 0.7) + (visual_sim * 0.3)
        return min(0.99, (max(0.0, final) ** 2) * 1.3) if final > 0.15 else final

    def generate_caption(self, model, inputs, proc, is_video=False):
        num_beams = self.settings.get('num_beams', 5)
        min_length = self.settings.get('min_length', 20)
        out = model.generate(**inputs, max_new_tokens=60, min_length=min_length, num_beams=num_beams, repetition_penalty=1.2)
        return proc.decode(out[0], skip_special_tokens=True)

    def run(self):
        try:
            device = str(self.worker_device_str)
            proc, model_gen, model_ret = get_engine_safe(device)
            
            if self.mode == 'vector':
                if self.query_img_path:
                    img = Image.open(self.query_img_path).convert('RGB')
                    inputs = proc(images=img, return_tensors="pt").to(device)
                    with torch.no_grad():
                        caption = self.generate_caption(model_gen, inputs, proc)
                        self.progress_update.emit(100, caption)
                        t_inputs = proc(text=caption, return_tensors="pt", padding=True).to(device)
                        self.query_text_vec = F.normalize(model_ret.text_proj(model_ret.text_encoder(**t_inputs).last_hidden_state[:, 0, :]), p=2, dim=-1)
                        self.visual_query_vec = F.normalize(model_ret.vision_proj(model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]), p=2, dim=-1)
                elif self.query_text:
                    t_inputs = proc(text=self.query_text, return_tensors="pt", padding=True).to(device)
                    with torch.no_grad():
                        self.query_text_vec = F.normalize(model_ret.text_proj(model_ret.text_encoder(**t_inputs).last_hidden_state[:, 0, :]), p=2, dim=-1)
                        self.visual_query_vec = self.query_text_vec
            else:
                if self.query_text: self.query_words = self.get_clean_words(self.query_text)

            for i, path in enumerate(self.target_paths):
                self.progress_update.emit(int((i/len(self.target_paths))*100), os.path.basename(path))
                if path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    self.process_vid(path, model_gen, model_ret, proc, device)
                else:
                    self.process_img(path, model_gen, model_ret, proc, device)
        except Exception as e:
            print(f"[AI WORKER ERROR]: {e}")
        finally:
            self.finished.emit()

    def process_img(self, path, model_gen, model_ret, proc, device):
        try:
            img = Image.open(path).convert('RGB')
            inputs = proc(images=img, return_tensors="pt").to(device)
            with torch.no_grad():
                cap = self.generate_caption(model_gen, inputs, proc)
                target_vec = F.normalize(model_ret.vision_proj(model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]), p=2, dim=-1)
                score = self.calculate_strict_keyword_score(cap, 0.0) if self.mode == 'keyword' else self.calculate_vector_score(cap, target_vec, proc, model_ret, device)
                self.result_found.emit({'path': path, 'score': score, 'caption': cap})
        except: pass

    def process_vid(self, path, model_gen, model_ret, proc, device):
        cap_vid = cv2.VideoCapture(path)
        fps = cap_vid.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap_vid.get(cv2.CAP_PROP_FRAME_COUNT))
        best_score, best_data = -1.0, None
        step = int(fps * 2) 

        for f_idx in range(0, total, step):
            cap_vid.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap_vid.read()
            if not ret: break
            pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            inputs = proc(images=pil, return_tensors="pt").to(device)
            with torch.no_grad():
                target_vec = F.normalize(model_ret.vision_proj(model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]), p=2, dim=-1)
                cap = self.generate_caption(model_gen, inputs, proc, is_video=True)
                score = self.calculate_strict_keyword_score(cap, 0.0) if self.mode == 'keyword' else self.calculate_vector_score(cap, target_vec, proc, model_ret, device)
                if score > best_score:
                    best_score = score
                    best_data = {'path': path, 'score': score, 'caption': cap, 'timestamp': f"{int(f_idx/fps//60)}:{int(f_idx/fps%60):02d}"}
        if best_data: self.result_found.emit(best_data)
        cap_vid.release()