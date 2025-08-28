# Question Similarity Search

This project provides a question similarity search tool using both TF-IDF and BERT embeddings to find the most similar questions from a Quora dataset.

## Features

- Preprocess questions with NLP techniques (tokenization, stopword removal, lemmatization).
- Generate embeddings using:
  - TF-IDF vectorization
  - BERT embeddings via Sentence Transformers
- Search for similar questions using cosine similarity.
- Two interfaces:
  - **Streamlit Web App** for interactive queries.
  - **Command Line Bot** for terminal interaction.

## Dataset

- Quora question pairs dataset (`data/quora.csv`).
- Only the first 10,000 rows are used for performance reasons.

