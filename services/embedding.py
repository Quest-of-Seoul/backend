"""Image Embedding Service - CLIP"""

import os
import logging
import hashlib
from typing import List, Optional, Tuple
from io import BytesIO
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("transformers or torch not installed")

_clip_model = None
_clip_processor = None
_device = None


def load_clip_model() -> Tuple[Optional[object], Optional[object], Optional[str]]:
    """Load CLIP model"""
    global _clip_model, _clip_processor, _device
    
    if not CLIP_AVAILABLE:
        logger.error("CLIP not available")
        return None, None, None
    
    if _clip_model is not None:
        return _clip_model, _clip_processor, _device
    
    try:
        logger.info("Loading CLIP model...")
        
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {_device}")
        
        model_name = "openai/clip-vit-base-patch32"
        _clip_model = CLIPModel.from_pretrained(model_name).to(_device)
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
        _clip_model.eval()
        
        logger.info("CLIP model loaded")
        return _clip_model, _clip_processor, _device
    
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}", exc_info=True)
        return None, None, None


def generate_image_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """Generate image embedding"""
    model, processor, device = load_clip_model()
    
    if model is None:
        logger.error("CLIP model not available")
        return None
    
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        inputs = processor(images=img, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        embedding = image_features.cpu().numpy().flatten().tolist()
        
        logger.info(f"Generated embedding: {len(embedding)} dimensions")
        return embedding
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        return None


def generate_embeddings_batch(
    image_bytes_list: List[bytes],
    batch_size: int = 32
) -> List[Optional[List[float]]]:
    """Batch generate embeddings"""
    model, processor, device = load_clip_model()
    
    if model is None:
        logger.error("CLIP model not available")
        return [None] * len(image_bytes_list)
    
    try:
        embeddings = []
        
        for i in range(0, len(image_bytes_list), batch_size):
            batch = image_bytes_list[i:i+batch_size]
            images = []
            
            for img_bytes in batch:
                try:
                    img = Image.open(BytesIO(img_bytes))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to load image: {e}")
                    images.append(None)
            
            valid_images = [img for img in images if img is not None]
            
            if valid_images:
                inputs = processor(images=valid_images, return_tensors="pt", padding=True)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    batch_features = model.get_image_features(**inputs)
                
                batch_features = batch_features / batch_features.norm(dim=-1, keepdim=True)
                batch_embeddings = batch_features.cpu().numpy()
                
                valid_idx = 0
                for img in images:
                    if img is not None:
                        embeddings.append(batch_embeddings[valid_idx].tolist())
                        valid_idx += 1
                    else:
                        embeddings.append(None)
            else:
                embeddings.extend([None] * len(batch))
            
            logger.info(f"Batch {i//batch_size + 1}: {len(valid_images)}/{len(batch)} processed")
        
        return embeddings
    
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}", exc_info=True)
        return [None] * len(image_bytes_list)


def generate_text_embedding(text: str) -> Optional[List[float]]:
    """Generate text embedding"""
    model, processor, device = load_clip_model()
    
    if model is None:
        logger.error("CLIP model not available")
        return None
    
    try:
        # CLIP 모델의 max_position_embeddings는 77이므로 truncation 필요
        inputs = processor(
            text=[text], 
            return_tensors="pt", 
            padding=True,
            truncation=True,
            max_length=77
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
        
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        embedding = text_features.cpu().numpy().flatten().tolist()
        
        logger.info(f"Generated text embedding: {len(embedding)} dimensions")
        return embedding
    
    except Exception as e:
        logger.error(f"Text embedding failed: {e}", exc_info=True)
        return None


def calculate_cosine_similarity(
    embedding1: List[float],
    embedding2: List[float]
) -> float:
    """Calculate cosine similarity"""
    try:
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)
        
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        similarity = (similarity + 1.0) / 2.0
        
        return float(similarity)
    
    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}", exc_info=True)
        return 0.0


def hash_image(image_bytes: bytes) -> str:
    """Generate SHA-256 hash of image"""
    return hashlib.sha256(image_bytes).hexdigest()


def preload_model():
    """Preload CLIP model"""
    logger.info("Preloading CLIP model...")
    load_clip_model()
    logger.info("CLIP model preloaded")


if os.getenv("PRELOAD_CLIP_MODEL", "false").lower() == "true":
    preload_model()
