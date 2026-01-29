import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForImageTextRetrieval
from PIL import Image

class BlipEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading BLIP Search Engine on {self.device}...")
        
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.model_gen = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        self.model_search = BlipForImageTextRetrieval.from_pretrained("Salesforce/blip-itm-base-coco").to(self.device)

    def get_image_features(self, pil_image):
        inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            feats = self.model_search.vision_model(inputs.pixel_values).last_hidden_state[:, 0, :]
        return feats

    def get_text_features(self, text_query):
        inputs = self.processor(text=text_query, return_tensors="pt").to(self.device)
        with torch.no_grad():
            feats = self.model_search.text_encoder(**inputs).last_hidden_state[:, 0, :]
        return feats

    def generate_caption(self, pil_image):
        inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model_gen.generate(**inputs, max_new_tokens=30)
            caption = self.processor.decode(out[0], skip_special_tokens=True)
        return caption