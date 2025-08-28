from sentence_transformers import SentenceTransformer

def get_bert_embeddings(corpus):
    """Generate BERT embeddings using Sentence Transformers."""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(corpus, convert_to_numpy=True)
    return embeddings, model
