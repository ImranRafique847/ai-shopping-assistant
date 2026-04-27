"""Test all components end to end"""
import boto3, json, os, numpy as np, faiss, tempfile
from dotenv import load_dotenv
load_dotenv()

s3 = boto3.client('s3', region_name='us-east-1',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

# Test 1: S3 FAISS index
print('Test 1: Loading FAISS from S3...')
with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp:
    s3.download_fileobj('ebay-restore-data', 'embeddings/faiss_index.bin', tmp)
    index = faiss.read_index(tmp.name)
print(f'  PASS: {index.ntotal} products loaded')

# Test 2: Titan Embeddings
print('Test 2: Titan Embeddings...')
body = json.dumps({'inputText': 'women dress', 'dimensions': 1024, 'normalize': True})
r = bedrock.invoke_model(modelId='amazon.titan-embed-text-v2:0', body=body,
    contentType='application/json', accept='application/json')
emb = np.array(json.loads(r['body'].read())['embedding'], dtype=np.float32)
print(f'  PASS: embedding shape {emb.shape}')

# Test 3: FAISS search
print('Test 3: FAISS search...')
scores, idxs = index.search(emb.reshape(1,-1), 3)
print(f'  PASS: top scores {scores[0]}')

# Test 4: Nova Micro without system
print('Test 4: Nova Micro (no system)...')
body = json.dumps({
    'messages': [{'role': 'user', 'content': [{'text': 'Say OK'}]}],
    'inferenceConfig': {'maxTokens': 10}
})
r = bedrock.invoke_model(modelId='amazon.nova-micro-v1:0', body=body,
    contentType='application/json', accept='application/json')
result = json.loads(r['body'].read())
print(f'  PASS: {result["output"]["message"]["content"][0]["text"]}')

# Test 5: Nova Micro with system
print('Test 5: Nova Micro (with system)...')
body = json.dumps({
    'messages': [{'role': 'user', 'content': [{'text': 'What are you?'}]}],
    'system': [{'text': 'You are a shopping assistant.'}],
    'inferenceConfig': {'maxTokens': 50}
})
r = bedrock.invoke_model(modelId='amazon.nova-micro-v1:0', body=body,
    contentType='application/json', accept='application/json')
result = json.loads(r['body'].read())
print(f'  PASS: {result["output"]["message"]["content"][0]["text"][:80]}')

print('\nALL TESTS PASSED ✓')
