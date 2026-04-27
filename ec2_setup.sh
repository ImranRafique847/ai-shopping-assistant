#!/bin/bash
# ec2_setup.sh — Run this on EC2 to install dependencies and run embeddings
# This script installs everything needed and runs the embedding job

echo "=== Installing system dependencies ==="
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv

echo "=== Creating virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python packages ==="
pip install --upgrade pip
pip install boto3 faiss-cpu numpy tqdm

echo "=== Downloading embedding script from S3 ==="
aws s3 cp s3://ebay-restore-data/scripts/ec2_embeddings.py ec2_embeddings.py

echo "=== Running embedding job ==="
AWS_REGION=us-east-1 \
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0 \
S3_BUCKET=ebay-restore-data \
S3_DATA_KEY=ebay_data.json \
S3_INDEX_KEY=embeddings/faiss_index.bin \
S3_METADATA_KEY=embeddings/metadata.json \
python ec2_embeddings.py

echo "=== Done! ==="
