import os
import warnings
from typing import List
import numpy as np
from app.core.config import settings

# Suppress noisy HF Hub warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")

class EmbeddingService:
    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"[!] FastEmbed notice: {e}. Using lightweight fallback generator.")
                self._model = "fallback"
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        model = self._get_model()
        if model != "fallback":
            try:
                embeddings_gen = model.embed(texts)
                return [embedding.tolist() for embedding in embeddings_gen]
            except Exception as e:
                print(f"[!] Error in FastEmbed generation: {e}")
        
        dim = settings.EMBEDDING_DIM
        results = []
        for text in texts:
            np.random.seed(abs(hash(text)) % (2**32))
            vec = np.random.randn(dim)
            vec = vec / np.linalg.norm(vec)
            results.append(vec.tolist())
        return results

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

embedding_service = EmbeddingService()
