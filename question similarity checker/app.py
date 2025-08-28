import streamlit as st
import pandas as pd
import numpy as np
import random

from utils.preprocessing import preprocess
from embeddings.tfidf_embedder import get_tfidf_embeddings
from embeddings.bert_embedder import get_bert_embeddings
from utils.similarity import find_similar

# --- Load Dataset ---
df = pd.read_csv("data/quora.csv").dropna().head(10000)
all_questions = pd.concat([df['question1'], df['question2']]).drop_duplicates().dropna().reset_index(drop=True)
processed_questions = all_questions.apply(preprocess)

# --- Generate embeddings ---
tfidf_embeddings, tfidf_vectorizer = get_tfidf_embeddings(processed_questions)
bert_embeddings, bert_model = get_bert_embeddings(processed_questions.tolist())

# --- Session State ---
if "target_idx" not in st.session_state:
    st.session_state.target_idx = random.randint(0, len(processed_questions) - 1)
    st.session_state.round = 1
    st.session_state.score = 0

# --- Game UI ---
st.title("🎯 Question Similarity Guessing Game")
st.write(f"Round {st.session_state.round} | Score: {st.session_state.score}")

user_query = st.text_input("🔍 Enter your guess question:")

if user_query:
    query_processed = preprocess(user_query)

    # TF-IDF similarity
    query_vec_tfidf = tfidf_vectorizer.transform([query_processed])
    results_tfidf = find_similar(query_vec_tfidf, tfidf_embeddings, processed_questions.tolist())
    top_text_tfidf, top_score_tfidf = results_tfidf[0]

    # BERT similarity
    query_vec_bert = bert_model.encode([query_processed], convert_to_numpy=True)
    results_bert = find_similar(query_vec_bert, bert_embeddings, processed_questions.tolist())
    top_text_bert, top_score_bert = results_bert[0]

    st.subheader("📌 TF-IDF Top Match")
    st.write(f"**Score:** {top_score_tfidf:.4f}  \n**Question:** {top_text_tfidf}")

    st.subheader("📌 BERT Top Match")
    st.write(f"**Score:** {top_score_bert:.4f}  \n**Question:** {top_text_bert}")

    # --- Game Logic ---
    target_question = processed_questions.iloc[st.session_state.target_idx]  # <-- FIXED
    if query_processed.strip() == target_question.strip():
        st.success("🎉 Correct! You guessed the target question!")
        st.session_state.score += 1
    else:
        st.warning("❌ Not the target question. Try again!")

# --- Reveal & Next Round ---
if st.button("Reveal Answer & Next Round"):
    st.info(f"✅ The target question was: **{all_questions.iloc[st.session_state.target_idx]}**")
    st.session_state.target_idx = random.randint(0, len(processed_questions) - 1)
    st.session_state.round += 1
    st.rerun()
