import open_clip
import torch
from PIL import Image
import os

os.environ["HF_HUB_OFFLINE"] = "1"

#comments baad me hata dena, abhi just for thoda understanding.

#provides pretrained clip models that can be used for text and image embeddings.
#PyTorch is the backend used by the clip model.
#PIL(Python Imaging Library) is used for image processing and manipulation.
#loads images from disk before preprocessing them for the clip model.

#loading clip model is expensive, we gotta do that once per run

_model = None
_preprocess = None
_tokenizer = None #for encode_text() we may use later
_device = None

def get_clip():
    global _model, _preprocess, _tokenizer, _device
    if _model is None:
        #prefer NVIDIA GPU if available, else fallback to CPU
        _device = "cuda" if torch.cuda.is_available() else "cpu"

        _model, _, _preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", 
            pretrained="laion2b_s34b_b79k"
        )
        #ignore second argument since we dont need to train the model, 
        # we just need the pretrained weights for inference.
        _tokenizer = open_clip.get_tokenizer("ViT-B-32")
        
        _model = _model.to(_device)
        _model.eval() #set to inference mode, not training mode
    
    return _model, _preprocess, _tokenizer, _device

def embed_image(image_path: str) -> list[float]:
    model, preprocess, _, device = get_clip()
    #we don't need tokenizer rn

    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device) 
    #resize, crop and normalize the image to get a tensor
    #torch expects "batch" as leading argument, so we add a batch dimension using unsqueeze(0)

    with torch.no_grad():
        features = model.encode_image(image_input)
        #encode_image() returns a tensor of shape (1, 512) for ViT
        #we use torch.no_grad() to avoid computing gradients since we are not training the model
        features = features / features.norm(dim=-1, keepdim=True)
        #return unit vector since only direction matters

    return features.squeeze(0).cpu().tolist() #normal python list to store in chromaDB

#test
if __name__ == "__main__":
    taj1 = embed_image("/home/ssrivastava/Downloads/test/taj1.jpg")
    taj2 = embed_image("/home/ssrivastava/Downloads/test/taj2.jpg")
    dog = embed_image("/home/ssrivastava/Downloads/test/dog.jpg")

    taj1 = torch.tensor(taj1)
    taj2 = torch.tensor(taj2)
    dog = torch.tensor(dog)

    sim_taj = torch.dot(taj1, taj2).item()
    sim_dog = torch.dot(taj1, dog).item()

    print(f"Taj to Taj : {sim_taj:.4f}")
    print(f"Taj to Dog : {sim_dog:.4f}") 