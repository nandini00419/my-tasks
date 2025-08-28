import numpy as np

def load_glove(path):
    """Load GloVe vectors from file."""
    print("Loading GloVe vectors...")
    model = {}
    with open(path, encoding="utf8") as f:
        for line in f:
            values = line.split()
            word = values[0]
            vector = np.array(values[1:], dtype='float32')
            model[word] = vector
    return model

def get_w2v_embedding(text, model, vector_size=300):
    """Generate average Word2Vec embedding for a text."""
    words = text.split()
    vectors = [model[w] for w in words if w in model]
    if len(vectors) == 0:
        return np.zeros(vector_size)
    return np.mean(vectors, axis=0)
