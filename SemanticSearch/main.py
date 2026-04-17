import pandas as pd
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from google.colab import userdata
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

print("Loading dataset...")
dataset = load_dataset("ag_news", split="train[:1000]")

documents = dataset["text"]

print(f"Loaded {len(documents)} documents.")
print(f"Sample: {documents[0][:100]}")

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Encoding documents...")
embeddings = model.encode(documents, show_progress_bar=True)
print(f"Computed embeddings for {len(embeddings)} documents with shape {embeddings.shape}.")

search_enginer = NearestNeighbors(n_neighbors=5, metric="cosine")
search_enginer.fit(embeddings)
print("Search engine ready.")

def semantic_search(query, top_k=3):
    query_embedding = model.encode([query])
    distances, indices = search_enginer.kneighbors(query_embedding, n_neighbors=top_k)
    print("Query:", query)
    print("-"*50)
    for i in range(top_k):
        doc_idx= indices[0][i]
        similarity=1-distances[0][i]
        print(f"Result {i+1}(Similarity : {similarity:.4f})")
        print(f"Text: {documents[int(doc_idx)][:150]}...\n")


semantic_search("Wall street and stock market trends")
semantic_search("Space exploration and rocket launches")

