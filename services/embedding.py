"""
Image Embedding service - CLIP 기반 이미지 벡터화
512차원 임베딩 생성 및 벡터 검색
"""

import os
from typing import List, Optional, Tuple
from io import BytesIO
from PIL import Image
import numpy as np

# CLIP 모델
try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("[Embedding] ⚠️ transformers or torch not installed. CLIP will be unavailable.")

# 전역 모델 캐싱
_clip_model = None
_clip_processor = None
_device = None


def load_clip_model() -> Tuple[Optional[object], Optional[object], Optional[str]]:
    """
    CLIP 모델 로드 (싱글톤 패턴)
    
    Returns:
        (model, processor, device)
    """
    global _clip_model, _clip_processor, _device
    
    if not CLIP_AVAILABLE:
        print("[Embedding] ❌ CLIP not available")
        return None, None, None
    
    # 이미 로드된 경우 재사용
    if _clip_model is not None:
        return _clip_model, _clip_processor, _device
    
    try:
        print("[Embedding] 🔄 Loading CLIP model...")
        
        # 디바이스 선택 (GPU 사용 가능하면 GPU)
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Embedding] 🖥️ Using device: {_device}")
        
        # CLIP 모델 로드 (openai/clip-vit-base-patch32)
        model_name = "openai/clip-vit-base-patch32"
        _clip_model = CLIPModel.from_pretrained(model_name).to(_device)
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
        
        # 평가 모드로 전환 (추론용)
        _clip_model.eval()
        
        print("[Embedding] ✅ CLIP model loaded successfully")
        return _clip_model, _clip_processor, _device
    
    except Exception as e:
        print(f"[Embedding] ❌ Failed to load CLIP model: {e}")
        return None, None, None


def generate_image_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """
    이미지로부터 512차원 임베딩 벡터 생성
    
    Args:
        image_bytes: 이미지 바이트 데이터
    
    Returns:
        512차원 임베딩 벡터 (리스트)
    """
    model, processor, device = load_clip_model()
    
    if model is None or processor is None:
        print("[Embedding] ❌ CLIP model not available")
        return None
    
    try:
        # 이미지 로드
        image = Image.open(BytesIO(image_bytes))
        
        # RGB 변환
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 이미지 전처리
        inputs = processor(images=image, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 추론 (gradient 계산 비활성화)
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # 정규화 (L2 norm)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # NumPy 배열로 변환 후 리스트로
        embedding = image_features.cpu().numpy().flatten().tolist()
        
        print(f"[Embedding] ✅ Generated embedding: {len(embedding)} dimensions")
        return embedding
    
    except Exception as e:
        print(f"[Embedding] ❌ Embedding generation failed: {e}")
        return None


def generate_embeddings_batch(
    image_bytes_list: List[bytes],
    batch_size: int = 8
) -> List[Optional[List[float]]]:
    """
    여러 이미지의 임베딩을 배치로 생성 (효율적)
    
    Args:
        image_bytes_list: 이미지 바이트 리스트
        batch_size: 배치 크기
    
    Returns:
        임베딩 벡터 리스트
    """
    model, processor, device = load_clip_model()
    
    if model is None or processor is None:
        print("[Embedding] ❌ CLIP model not available")
        return [None] * len(image_bytes_list)
    
    embeddings = []
    
    try:
        # 배치로 처리
        for i in range(0, len(image_bytes_list), batch_size):
            batch = image_bytes_list[i:i+batch_size]
            
            # 이미지 로드 및 전처리
            images = []
            for img_bytes in batch:
                try:
                    img = Image.open(BytesIO(img_bytes))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    print(f"[Embedding] ⚠️ Failed to load image: {e}")
                    images.append(None)
            
            # 유효한 이미지만 처리
            valid_images = [img for img in images if img is not None]
            
            if not valid_images:
                embeddings.extend([None] * len(batch))
                continue
            
            # 배치 전처리
            inputs = processor(images=valid_images, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # 추론
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
            
            # 정규화
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # NumPy 배열로 변환
            batch_embeddings = image_features.cpu().numpy()
            
            # 결과 매핑 (None 이미지 포함)
            valid_idx = 0
            for img in images:
                if img is not None:
                    embeddings.append(batch_embeddings[valid_idx].tolist())
                    valid_idx += 1
                else:
                    embeddings.append(None)
            
            print(f"[Embedding] ✅ Batch {i//batch_size + 1}: {len(valid_images)}/{len(batch)} processed")
        
        return embeddings
    
    except Exception as e:
        print(f"[Embedding] ❌ Batch embedding failed: {e}")
        return [None] * len(image_bytes_list)


def generate_text_embedding(text: str) -> Optional[List[float]]:
    """
    텍스트로부터 임베딩 벡터 생성 (이미지-텍스트 검색용)
    
    Args:
        text: 입력 텍스트
    
    Returns:
        512차원 임베딩 벡터
    """
    model, processor, device = load_clip_model()
    
    if model is None or processor is None:
        print("[Embedding] ❌ CLIP model not available")
        return None
    
    try:
        # 텍스트 전처리
        inputs = processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 추론
        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
        
        # 정규화
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # 리스트로 변환
        embedding = text_features.cpu().numpy().flatten().tolist()
        
        print(f"[Embedding] ✅ Generated text embedding: {len(embedding)} dimensions")
        return embedding
    
    except Exception as e:
        print(f"[Embedding] ❌ Text embedding failed: {e}")
        return None


def calculate_cosine_similarity(
    embedding1: List[float],
    embedding2: List[float]
) -> float:
    """
    두 임베딩 벡터 간의 코사인 유사도 계산
    
    Args:
        embedding1: 첫 번째 벡터
        embedding2: 두 번째 벡터
    
    Returns:
        코사인 유사도 (0.0 ~ 1.0)
    """
    try:
        # NumPy 배열로 변환
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # 코사인 유사도 계산
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        similarity = dot_product / (norm1 * norm2)
        
        # 0~1 범위로 정규화
        similarity = (similarity + 1.0) / 2.0
        
        return float(similarity)
    
    except Exception as e:
        print(f"[Embedding] ❌ Similarity calculation failed: {e}")
        return 0.0


def hash_image(image_bytes: bytes) -> str:
    """
    이미지 해시 생성 (중복 방지용)
    
    Args:
        image_bytes: 이미지 바이트 데이터
    
    Returns:
        SHA-256 해시 문자열
    """
    import hashlib
    return hashlib.sha256(image_bytes).hexdigest()


def preload_model():
    """
    서버 시작 시 CLIP 모델 미리 로드 (첫 요청 지연 방지)
    """
    print("[Embedding] 🚀 Preloading CLIP model...")
    load_clip_model()
    print("[Embedding] ✅ Model preload complete")


# 환경 변수로 자동 로드 설정 가능
if os.getenv("PRELOAD_CLIP_MODEL", "false").lower() == "true":
    preload_model()
