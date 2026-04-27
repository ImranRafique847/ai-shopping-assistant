"""
embeddings.py — Build and save FAISS index from ebay_data.json
using Amazon Titan Embeddings V2 via AWS Bedrock.

Usage:
    python embeddings.py
"""

import json
import os
import pickle
import numpy as np
import faiss
import boto3
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

AWS_REGION        = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
DATA_FILE         = os.getenv("DATA_FILE", "data/ebay_data.json")
INDEX_FILE        = os.getenv("INDEX_FILE", "data/faiss_index.bin")
METADATA_FILE     = os.getenv("METADATA_FILE", "data/metadata.json")

# Titan Embeddings V2 dimension
EMBEDDING_DIM = 1024


def build_text(item: dict) -> str:
    """Build a rich text representation of a product for embedding."""
    parts = []

    if item.get("product_name"):
        parts.append(item["product_name"])
    if item.get("category"):
        parts.append(f"Category: {item['category']}")
    if item.get("price"):
        parts.append(f"Price: {item['price']}")
    if item.get("condition"):
        parts.append(f"Condition: {item['condition']}")
    if item.get("seller_location"):
        parts.append(f"Location: {item['seller_location']}")

    # Item specifics (brand, size, color, material etc.)
    specifics = item.get("item_specifics", {})
    if specifics:
        spec_text = ", ".join(f"{k}: {v}" for k, v in list(specifics.items())[:10])
        parts.append(f"Details: {spec_text}")

    if item.get("seller_description"):
        parts.append(item["seller_description"][:500])

    return " | ".join(parts)


def get_embedding(client, text: str) -> np.ndarray:
    """Get embedding from Amazon Titan Embeddings V2."""
    body = json.dumps({
        "inputText": text[:8000],  # Titan V2 max input
        "dimensions": EMBEDDING_DIM,
        "normalize": True
    })
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    result = json.loads(response["body"].read())
    return np.array(result["embedding"], dtype=np.float32)


def build_index():
    print("Loading data...")
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total items: {len(data)}")

    # Filter items with at least a product name
    data = [item for item in data if item.get("product_name")]
    print(f"Valid items: {len(data)}")

    client = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    print(f"\nGenerating embeddings using {EMBEDDING_MODEL}...")
    embeddings = []
    metadata = []
    failed = 0

    for i, item in enumerate(tqdm(data)):
        try:
            text = build_text(item)
            emb = get_embedding(client, text)
            embeddings.append(emb)
            metadata.append({
                "item_id":                item.get("item_id", ""),
                "product_name":           item.get("product_name", ""),
                "category":               item.get("category", ""),
                "price":                  item.get("price", ""),
                "original_price":         item.get("original_price", ""),
                "condition":              item.get("condition", ""),
                "seller_name":            item.get("seller_name", ""),
                "seller_feedback":        item.get("seller_feedback", ""),
                "seller_feedback_percent":item.get("seller_feedback_percent", ""),
                "seller_location":        item.get("seller_location", ""),
                "image_urls":             item.get("image_urls", [])[:3],
                "product_url":            item.get("product_url", ""),
                "item_specifics":         item.get("item_specifics", {}),
            })
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"\n  [!] Failed item {i}: {str(e)[:80]}")

    print(f"\nEmbedded: {len(embeddings)} | Failed: {failed}")

    # Build FAISS index
    print("Building FAISS index...")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product (cosine on normalized vectors)
    matrix = np.stack(embeddings)
    index.add(matrix)

    # Save
    os.makedirs("data", exist_ok=True)
    faiss.write_index(index, INDEX_FILE)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    print(f"\n✓ Index saved to {INDEX_FILE}")
    print(f"✓ Metadata saved to {METADATA_FILE}")
    print(f"✓ Total vectors: {index.ntotal}")


if __name__ == "__main__":
    build_index()
