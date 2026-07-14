from PIL import Image
from cortex.shared.models import get_clip
import torch

def embed_image(image_path: str) -> list[float]:
    model, preprocess, _, device = get_clip()

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

import base64
from io import BytesIO

def make_thumbnail_base64(file_path: str, max_size: int = 120) -> str:
    img = Image.open(file_path).convert("RGB")
    img.thumbnail((max_size, max_size))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"

# #test
# if __name__ == "__main__":
#     taj1 = embed_image("/home/ssrivastava/Downloads/test/taj1.jpg")
#     taj2 = embed_image("/home/ssrivastava/Downloads/test/taj2.jpg")
#     dog = embed_image("/home/ssrivastava/Downloads/test/dog.jpg")

#     taj1 = torch.tensor(taj1)
#     taj2 = torch.tensor(taj2)
#     dog = torch.tensor(dog)

#     sim_taj = torch.dot(taj1, taj2).item()
#     sim_dog = torch.dot(taj1, dog).item()

#     print(f"Taj to Taj : {sim_taj:.4f}")
#     print(f"Taj to Dog : {sim_dog:.4f}") 