from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForImageTextRetrieval
import torch

def download():
    print("🚀 STARTING TERMINAL DOWNLOAD...")
    
    models = [
        ("Salesforce/blip-image-captioning-base", BlipForConditionalGeneration),
        ("Salesforce/blip-itm-base-coco", BlipForImageTextRetrieval)
    ]
    
    processor_name = "Salesforce/blip-image-captioning-base"
    
    print(f"📦 Downloading Processor: {processor_name}")
    BlipProcessor.from_pretrained(processor_name)
    
    for model_id, model_class in models:
        print(f"\n📦 Downloading Model: {model_id} (this is ~900MB, please wait)")
        model_class.from_pretrained(model_id)
        
    print("\n✅ DONE! All models are downloaded. You can now run main.py")

if __name__ == "__main__":
    download()