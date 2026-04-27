"""
ec2_embeddings.py — Runs on EC2 to build FAISS index from S3 data
and saves results back to S3.

This script:
1. Downloads ebay_data.json from S3
2. Calls AWS Bedrock Titan Embeddings for each product
3. Builds FAISS index
4. Uploads faiss_index.bin + metadata.json back to S3

Usage on EC2:
    python ec2_embeddings.py
"""

import json
import os
import tempfile
import numpy as np
import faiss
import boto3
from tqdm import tqdm

# ── Config — uses EC2 IAM role, no hardcoded keys needed ──────
AWS_REGION      = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
S3_BUCKET       = os.getenv("S3_BUCKET", "ebay-restore-data")
S3_DATA_KEY     = os.getenv("S3_DATA_KEY", "ebay_data.json")
S3_INDEX_KEY    = os.getenv("S3_INDEX_KEY", "embeddings/faiss_index.bin")
S3_METADATA_KEY = os.getenv("S3_METADATA_KEY", "embeddings/metadata.json")
EMBEDDING_DIM   = 1024
BATCH_SIZE      = 10  # process 10 items then save progress


def build_text(item: dict) -> str:
    """Build rich text from product for embedding."""
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
    specifics = item.get("item_specifics", {})
    if specifics:
        spec_text = ", ".join(f"{k}: {v}" for k, v in list(specifics.items())[:10])
        parts.append(f"Details: {spec_text}")
    if item.get("seller_description"):
        parts.append(item["seller_description"][:500])
    return " | ".join(parts)


def get_embedding(bedrock_client, text: str, retries: int = 5) -> np.ndarray:
    """Get embedding from Amazon Titan Embeddings V2 with retry on throttling."""
    import time
    body = json.dumps({
        "inputText": text[:8000],
        "dimensions": EMBEDDING_DIM,
        "normalize": True
    })
    for attempt in range(retries):
        try:
            response = bedrock_client.invoke_model(
                modelId=EMBEDDING_MODEL,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            result = json.loads(response["body"].read())
            return np.array(result["embedding"], dtype=np.float32)
        except Exception as e:
            if "ThrottlingException" in str(e) and attempt < retries - 1:
                wait = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
                time.sleep(wait)
            else:
                raise


def main():
    # ── AWS clients — uses EC2 IAM role automatically ─────────
    s3      = boto3.client("s3", region_name=AWS_REGION)
    bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    # ── Step 1: Download data from S3 ─────────────────────────
    print(f"Downloading s3://{S3_BUCKET}/{S3_DATA_KEY} ...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        s3.download_fileobj(S3_BUCKET, S3_DATA_KEY, tmp)
        tmp_path = tmp.name

    with open(tmp_path, encoding="utf-8") as f:
        data = json.load(f)
    os.unlink(tmp_path)

    print(f"Total items loaded: {len(data)}")
    data = [item for item in data if item.get("product_name")]
    print(f"Valid items: {len(data)}")

    # ── Step 2: Generate embeddings ───────────────────────────
    print(f"\nGenerating embeddings using {EMBEDDING_MODEL}...")
    embeddings = []
    metadata   = []
    failed     = 0

    for i, item in enumerate(tqdm(data)):
        try:
            text = build_text(item)
            emb  = get_embedding(bedrock, text)
            embeddings.append(emb)
            metadata.append({
                "item_id":                 item.get("item_id", ""),
                "product_name":            item.get("product_name", ""),
                "category":                item.get("category", ""),
                "price":                   item.get("price", ""),
                "original_price":          item.get("original_price", ""),
                "condition":               item.get("condition", ""),
                "seller_name":             item.get("seller_name", ""),
                "seller_feedback":         item.get("seller_feedback", ""),
                "seller_feedback_percent": item.get("seller_feedback_percent", ""),
                "seller_location":         item.get("seller_location", ""),
                "image_urls":              item.get("image_urls", [])[:3],
                "product_url":             item.get("product_url", ""),
                "item_specifics":          item.get("item_specifics", {}),
            })
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"\n  [!] Failed item {i}: {str(e)[:80]}")

    print(f"\nEmbedded: {len(embeddings)} | Failed: {failed}")

    # ── Step 3: Build FAISS index ─────────────────────────────
    print("Building FAISS index...")
    index  = faiss.IndexFlatIP(EMBEDDING_DIM)
    matrix = np.stack(embeddings)
    index.add(matrix)
    print(f"Total vectors in index: {index.ntotal}")

    # ── Step 4: Save and upload to S3 ─────────────────────────
    print("\nUploading to S3...")

    # Save FAISS index
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        faiss.write_index(index, tmp.name)
        s3.upload_file(tmp.name, S3_BUCKET, S3_INDEX_KEY)
        os.unlink(tmp.name)
    print(f"✓ FAISS index uploaded to s3://{S3_BUCKET}/{S3_INDEX_KEY}")

    # Save metadata
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(metadata, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    s3.upload_file(tmp_path, S3_BUCKET, S3_METADATA_KEY)
    os.unlink(tmp_path)
    print(f"✓ Metadata uploaded to s3://{S3_BUCKET}/{S3_METADATA_KEY}")

    print("\n✅ Done! Embeddings are ready on S3.")
    print(f"   Index  : s3://{S3_BUCKET}/{S3_INDEX_KEY}")
    print(f"   Metadata: s3://{S3_BUCKET}/{S3_METADATA_KEY}")


if __name__ == "__main__":
    main()
