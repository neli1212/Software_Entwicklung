import torch, cv2, os, re, threading, shutil
import torch.nn.functional as F
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForImageTextRetrieval

_GLOBAL_ENGINE = {"processor": None, "model_gen": None, "model_ret": None, "current_model": None}
_ENGINE_LOCK = threading.Lock() 

MODEL_PATH = os.path.join(os.getcwd(), "ai_models")

AVAILABLE_MODELS = {
    "Base ": {
        "cap": "Salesforce/blip-image-captioning-base",
        "ret": "Salesforce/blip-itm-base-coco",
        "folder": "blip_base"
    },
    "Large ": {
        "cap": "Salesforce/blip-image-captioning-large",
        "ret": "Salesforce/blip-itm-large-coco",
        "folder": "blip_large"
    }
}

def check_model_downloaded(model_key):
    """Prüft, ob der Ordner für das Modell existiert und Daten enthält."""
    if model_key not in AVAILABLE_MODELS: return False
    folder_path = os.path.join(MODEL_PATH, AVAILABLE_MODELS[model_key]["folder"])
    return os.path.exists(folder_path) and len(os.listdir(folder_path)) > 0

def delete_local_model(model_key):
    """Löscht die Dateien eines Modells, um Festplattenspeicher freizugeben."""
    global _GLOBAL_ENGINE
    if model_key not in AVAILABLE_MODELS: return False
    folder_path = os.path.join(MODEL_PATH, AVAILABLE_MODELS[model_key]["folder"])
    
    with _ENGINE_LOCK:
        if _GLOBAL_ENGINE.get("current_model") == model_key:
            _GLOBAL_ENGINE["processor"] = None
            _GLOBAL_ENGINE["model_gen"] = None
            _GLOBAL_ENGINE["model_ret"] = None
            _GLOBAL_ENGINE["current_model"] = None
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                return True
            except:
                return False
    return True

def get_engine_safe(device_string, model_key):
    """Lädt das spezifisch ausgewählte KI-Modell."""
    global _GLOBAL_ENGINE
    with _ENGINE_LOCK: 
        if _GLOBAL_ENGINE["processor"] is None or _GLOBAL_ENGINE.get("current_model") != model_key:
            print(f" [AI] LADE MODELL '{model_key}' VON: {MODEL_PATH}")
            dev = torch.device(device_string)
      
            _GLOBAL_ENGINE["processor"] = None
            _GLOBAL_ENGINE["model_gen"] = None
            _GLOBAL_ENGINE["model_ret"] = None
            if torch.cuda.is_available(): torch.cuda.empty_cache()

            m_info = AVAILABLE_MODELS[model_key]
            specific_cache_dir = os.path.join(MODEL_PATH, m_info["folder"])
            os.makedirs(specific_cache_dir, exist_ok=True)
            
            _GLOBAL_ENGINE["processor"] = BlipProcessor.from_pretrained(m_info["ret"], cache_dir=specific_cache_dir)
            _GLOBAL_ENGINE["model_gen"] = BlipForConditionalGeneration.from_pretrained(m_info["cap"], cache_dir=specific_cache_dir).to(dev)
            _GLOBAL_ENGINE["model_ret"] = BlipForImageTextRetrieval.from_pretrained(m_info["ret"], cache_dir=specific_cache_dir).to(dev)
            _GLOBAL_ENGINE["current_model"] = model_key
            
            print(f"[AI] ENGINES BEREIT AUF {str(dev).upper()}")
    return _GLOBAL_ENGINE["processor"], _GLOBAL_ENGINE["model_gen"], _GLOBAL_ENGINE["model_ret"]

class ModelLoader(QThread):
    finished = Signal()
    def __init__(self, model_key):
        super().__init__()
        self.target_dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_key = model_key

    def run(self):
        try:
            get_engine_safe(self.target_dev, self.model_key)
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
        self.model_key = self.settings.get('model_key', list(AVAILABLE_MODELS.keys())[0])
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
        text_sim = 0.0
        if self.query_text_vec is not None:
            inputs = proc(text=target_caption, return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                text_outputs = model_ret.text_encoder(**inputs)
                target_cap_vec = model_ret.text_proj(text_outputs.last_hidden_state[:, 0, :])
                target_cap_vec = F.normalize(target_cap_vec, p=2, dim=-1)
            text_sim = F.cosine_similarity(self.query_text_vec, target_cap_vec).item()

        visual_sim = 0.0
        if self.visual_query_vec is not None:
            visual_sim = F.cosine_similarity(self.visual_query_vec, target_visual_vec).item()

        # 1. Rohe KI-Ähnlichkeit (50% Text, 50% Bild)
        raw_sim = (max(0.0, text_sim) * 0.5) + (max(0.0, visual_sim) * 0.5)
        
        # --- NEUE SKALIERUNG ---
        # Wir definieren das typische Grundrauschen (baseline) und den realistischen Spitzenwert (max_expected)
        baseline = 0.22
        max_expected = 0.65
        
        # Alles was unter oder gleich dem Grundrauschen ist, ist kein Treffer -> 0%
        if raw_sim <= baseline:
            return 0.0
            
        # Wir strecken den echten Bereich (0.22 bis 0.65) auf 0.0 bis 1.0 (0% bis 100%)
        adjusted_sim = (raw_sim - baseline) / (max_expected - baseline)
        
        # Verhindern, dass Werte über 100% schießen, falls das Modell doch mal >0.65 ausgibt
        adjusted_sim = min(1.0, adjusted_sim)
        
        # Eine sanfte Kurve anlegen, damit echte Treffer stabile hohe Werte zeigen
        final_score = adjusted_sim ** 0.8 
        
        return min(0.999, final_score)

    def generate_caption(self, model, inputs, proc, is_video=False):
        num_beams = self.settings.get('num_beams', 5)
        min_length = self.settings.get('min_length', 20)
        out = model.generate(**inputs, max_new_tokens=60, min_length=min_length, num_beams=num_beams, repetition_penalty=1.2)
        return proc.decode(out[0], skip_special_tokens=True)

    def run(self):
        try:
            device = str(self.worker_device_str)
            proc, model_gen, model_ret = get_engine_safe(device, self.model_key)
            
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
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                return

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0 or fps != fps: 
                fps = 25.0
            

            interval_sec = 2 
            frame_skip = int(fps * interval_sec)
            if frame_skip == 0:
                frame_skip = 1

            best_score = -1.0
            best_caption = "No content detected."
            
            frame_idx = 0
            while True:

                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                success, frame = cap.read()
                
                if not success:
                    break 
                current_time_sec = frame_idx / fps
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                inputs = proc(images=pil_img, return_tensors="pt").to(device)
                
                caption = self.generate_caption(model_gen, inputs, proc)
                
                with torch.no_grad():
                    target_vec = F.normalize(model_ret.vision_proj(model_ret.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]), p=2, dim=-1)
                
                if self.mode == 'keyword':
                    score = self.calculate_strict_keyword_score(caption, 0.0)
                else:
                    score = self.calculate_vector_score(caption, target_vec, proc, model_ret, device)

                if score > best_score:
                    best_score = score
                    m, s = divmod(int(current_time_sec), 60)
                    best_time_str = f"{m:02d}:{s:02d}"
                    best_caption = f"[VIDEO {best_time_str}] {caption}"

                frame_idx += frame_skip

            cap.release()
        
            if best_score >= 0.0:
                self.result_found.emit({'path': path, 'caption': best_caption, 'score': best_score})

        except Exception as e:
            print(f"[Video Process Error] {path}: {e}")
            if 'cap' in locals() and cap.isOpened():
                cap.release()