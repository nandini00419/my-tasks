import os
import requests
import zipfile

# URL for GloVe embeddings
url = "http://nlp.stanford.edu/data/glove.6B.zip"
zip_path = "data/glove.6B.zip"
extract_path = "data"

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Download file if not exists
if not os.path.exists(zip_path):
    print("Downloading GloVe embeddings...")
    response = requests.get(url, stream=True)
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    print("Download complete!")

# Unzip if not already done
if not os.path.exists(os.path.join(extract_path, "glove.6B.300d.txt")):
    print("Extracting GloVe embeddings...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extraction complete!")

print("GloVe embeddings are ready in the 'data/' folder.")
