import pandas as pd
from utils.preprocessing import preprocess
from embeddings.tfidf_embedder import get_tfidf_embeddings
from embeddings.bert_embedder import get_bert_embeddings
from utils.similarity import find_similar
import numpy as np

# Step 1: Load dataset
df = pd.read_csv("data/quora.csv").dropna().head(10000)
all_questions = pd.concat([df['question1'], df['question2']]).drop_duplicates().dropna()

# Step 2: Preprocess
print("Preprocessing questions...")
processed_questions = all_questions.apply(preprocess)

# Step 3a: TF-IDF
print("Generating TF-IDF embeddings...")
tfidf_embeddings, tfidf_vectorizer = get_tfidf_embeddings(processed_questions)

# Step 3b: BERT
print("Generating BERT embeddings...")
bert_embeddings, bert_model = get_bert_embeddings(processed_questions.tolist())

print("\nChatbot is ready! Type 'exit' to quit.\n")

# Step 4: Interactive loop
while True:
    query = input("You: ")
    if query.lower() in ["exit", "quit", "bye"]:
        print("Bot: Goodbye! 👋")
        break

    query_processed = preprocess(query)

    # TF-IDF results
    query_vec_tfidf = tfidf_vectorizer.transform([query_processed])
    results_tfidf = find_similar(query_vec_tfidf, tfidf_embeddings, processed_questions.tolist())
    top_text_tfidf, top_score_tfidf = results_tfidf[0]  # text first, score second

    # BERT results
    query_vec_bert = bert_model.encode([query_processed], convert_to_numpy=True)
    results_bert = find_similar(query_vec_bert, bert_embeddings, processed_questions.tolist())
    top_text_bert, top_score_bert = results_bert[0]

    print("\n--- TF-IDF Top Match ---")
    print(f"{top_score_tfidf:.4f} | {top_text_tfidf}")

    print("\n--- BERT Top Match ---")
    print(f"{top_score_bert:.4f} | {top_text_bert}")
    print()
