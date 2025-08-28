from sklearn.feature_extraction.text import TfidfVectorizer

def get_tfidf_embeddings(corpus):
    """Generate TF-IDF embeddings."""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    return tfidf_matrix, vectorizer
