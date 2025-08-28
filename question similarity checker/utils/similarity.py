import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def find_similar(query_vec, embeddings, corpus, top_n=5):
    """Find top N similar texts based on cosine similarity."""
    sims = cosine_similarity(query_vec, embeddings).flatten()
    top_indices = sims.argsort()[-top_n:][::-1]
    results = [(corpus[idx], sims[idx]) for idx in top_indices]
    return results
