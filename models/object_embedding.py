import torch
import clip
from PIL import Image
import numpy as np

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def generate_embedding_from_crop(crop_path) -> np.ndarray:
    """
    Generate CLIP embedding from an image crop.
    :param crop_path: Path to the image crop
    :return: Numpy array representing the embedding (512,)
    """
    image = preprocess(Image.open(crop_path)).unsqueeze(0).to(device) #preprocess transforms the image for CLIP model : resize, center crop, normalize and unsqueeze to add batch dimension
    with torch.no_grad(): #no_grad : no gradient calculation, no train only inference
        embedding = model.encode_image(image) #encode_image : generate the image embedding ; encoder 
        embedding /= embedding.norm(dim=-1, keepdim=True) #normalize the embedding to unit length for cos similarity
    embedding = embedding.cpu().numpy().flatten() #remove batch dimension and convert to numpy
    return embedding