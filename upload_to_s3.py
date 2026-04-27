"""
upload_to_s3.py — Uploads project files to S3 bucket
Uploads:
  - data/ebay_data.json      → s3://ebay-restore-data/ebay_data.json
  - ec2_embeddings.py        → s3://ebay-restore-data/scripts/ec2_embeddings.py
  - ec2_requirements.txt     → s3://ebay-restore-data/scripts/ec2_requirements.txt
  - ec2_setup.sh             → s3://ebay-restore-data/scripts/ec2_setup.sh

Usage:
    python upload_to_s3.py
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = "ebay-restore-data"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# Files to upload: (local path, s3 key)
FILES = [
    ("data/ebay_data.json",    "ebay_data.json"),
    ("ec2_embeddings.py",      "scripts/ec2_embeddings.py"),
    ("ec2_requirements.txt",   "scripts/ec2_requirements.txt"),
    ("ec2_setup.sh",           "scripts/ec2_setup.sh"),
]

print(f"Uploading files to s3://{S3_BUCKET}/\n")

for local_path, s3_key in FILES:
    if not os.path.exists(local_path):
        print(f"  [!] Skipping {local_path} — file not found")
        continue
    try:
        s3.upload_file(local_path, S3_BUCKET, s3_key)
        print(f"  ✓ {local_path} → s3://{S3_BUCKET}/{s3_key}")
    except Exception as e:
        print(f"  [!] Failed {local_path}: {e}")

print("\n✅ Upload complete.")
print(f"\nNext step: Launch EC2 and run:")
print(f"  aws s3 cp s3://{S3_BUCKET}/scripts/ec2_setup.sh . && bash ec2_setup.sh")
