"""
main.py — FastAPI backend for AI Shopping Assistant
Implements Corrective RAG (CRAG) pattern:
  1. LLM rewrites user query for better retrieval
  2. FAISS searches locally (index loaded from S3 on startup)
  3. LLM generates final response
"""

import json
import os
import tempfile
import numpy as np
import faiss
import boto3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

AWS_REGION      = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
CHAT_MODEL      = os.getenv("CHAT_MODEL_ID", "amazon.nova-micro-v1:0")
S3_BUCKET       = os.getenv("S3_BUCKET", "ebay-restore-data")
S3_INDEX_KEY    = os.getenv("S3_INDEX_KEY", "embeddings/faiss_index.bin")
S3_METADATA_KEY = os.getenv("S3_METADATA_KEY", "embeddings/metadata.json")
EMBEDDING_DIM   = 1024
TOP_K           = 8

app = FastAPI(title="AI Shopping Assistant")

# ── AWS clients ────────────────────────────────────────────────
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# ── Load FAISS index from S3 on startup ───────────────────────
print("Loading FAISS index from S3...")
with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
    s3.download_fileobj(S3_BUCKET, S3_INDEX_KEY, tmp)
    tmp_path = tmp.name

index = faiss.read_index(tmp_path)
os.unlink(tmp_path)

meta_obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_METADATA_KEY)
metadata = json.loads(meta_obj["Body"].read().decode("utf-8"))
print(f"✓ Loaded {index.ntotal} products")


# ── LLM caller — supports Titan and Claude ─────────────────────

def call_llm(prompt: str, system: str = "") -> str:
    """Call LLM — supports Titan, Nova and Claude models."""
    if "titan" in CHAT_MODEL:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        body = json.dumps({
            "inputText": full_prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1024,
                "temperature": 0.7,
            }
        })
        response = bedrock.invoke_model(
            modelId=CHAT_MODEL, body=body,
            contentType="application/json", accept="application/json"
        )
        result = json.loads(response["body"].read())
        return result["results"][0]["outputText"].strip()
    elif "nova" in CHAT_MODEL:
        # Amazon Nova format
        body_dict = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 1024, "temperature": 0.7}
        }
        if system:
            body_dict["system"] = [{"text": system}]
        body = json.dumps(body_dict)
        response = bedrock.invoke_model(
            modelId=CHAT_MODEL, body=body,
            contentType="application/json", accept="application/json"
        )
        result = json.loads(response["body"].read())
        return result["output"]["message"]["content"][0]["text"].strip()
    else:
        # Anthropic Claude format
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = bedrock.invoke_model(
            modelId=CHAT_MODEL, body=body,
            contentType="application/json", accept="application/json"
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]


# ── CRAG Step 1: Query Rewriter ────────────────────────────────

def rewrite_query(user_message: str, history: list) -> str:
    """
    CRAG Step 1 — Strong query rewriter.
    Understands user intent from conversation history and rewrites
    into a precise search query for maximum retrieval accuracy.
    """
    history_context = ""
    if history:
        recent = history[-6:]
        history_context = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in recent
        )

    prompt = f"""You are an expert search query optimizer for an eBay fashion store.

Your task: Rewrite the user's message into the most effective search query to retrieve relevant fashion products.

Rules:
1. Extract ALL relevant attributes: product type, gender, age group, color, size, price range, brand, condition, style
2. Fix spelling mistakes and expand abbreviations
3. Use conversation history to understand follow-up questions (e.g. "show me cheaper ones" → use previous product type)
4. Be specific — "women casual summer dress floral" is better than "dress"
5. Return ONLY the rewritten search query — no explanation, no punctuation at end

Conversation history:
{history_context if history_context else "No previous conversation"}

User message: {user_message}

Optimized search query:"""

    rewritten = call_llm(prompt)
    rewritten = rewritten.strip().strip('"').strip("'")
    print(f"[CRAG] Original : {user_message}")
    print(f"[CRAG] Rewritten: {rewritten}")
    return rewritten


# ── CRAG Step 2: FAISS Search ──────────────────────────────────

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Amazon Titan Embeddings V2."""
    body = json.dumps({
        "inputText": text[:8000],
        "dimensions": EMBEDDING_DIM,
        "normalize": True
    })
    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    result = json.loads(response["body"].read())
    return np.array(result["embedding"], dtype=np.float32)


def search_products(query: str) -> list:
    """Search FAISS index with category, price and condition filtering."""
    import re

    emb = get_embedding(query).reshape(1, -1)
    # Search many more to allow filtering
    scores, indices = index.search(emb, TOP_K * 6)

    query_lower = query.lower()

    # ── Category detection ─────────────────────────────────────
    shoe_keywords = ['shoe', 'boot', 'sneaker', 'loafer', 'heel', 'sandal', 'oxford', 'slipper', 'footwear']
    bag_keywords = ['bag', 'handbag', 'purse', 'backpack', 'tote', 'clutch', 'satchel']
    trouser_keywords = ['trouser', 'pant', 'jean', 'legging', 'jogger', 'chino', 'shorts']
    dress_keywords = ['dress', 'gown', 'skirt', 'frock']

    is_shoe_query = any(k in query_lower for k in shoe_keywords)
    is_bag_query = any(k in query_lower for k in bag_keywords)
    is_trouser_query = any(k in query_lower for k in trouser_keywords)
    is_dress_query = any(k in query_lower for k in dress_keywords)

    # ── Price filter detection ─────────────────────────────────
    max_price = None
    min_price = None
    price_match = re.search(r'under\s*\$?(\d+(?:\.\d+)?)', query_lower)
    if price_match:
        max_price = float(price_match.group(1))
    price_match2 = re.search(r'below\s*\$?(\d+(?:\.\d+)?)', query_lower)
    if price_match2:
        max_price = float(price_match2.group(1))
    price_match3 = re.search(r'less than\s*\$?(\d+(?:\.\d+)?)', query_lower)
    if price_match3:
        max_price = float(price_match3.group(1))
    price_match4 = re.search(r'over\s*\$?(\d+(?:\.\d+)?)', query_lower)
    if price_match4:
        min_price = float(price_match4.group(1))

    # ── Condition filter detection ─────────────────────────────
    want_used = any(w in query_lower for w in ['used', 'pre-owned', 'preowned', 'second hand', 'secondhand'])
    want_new = any(w in query_lower for w in ['new', 'brand new', 'unused'])

    results = []
    seen_names = set()
    seen_urls = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        item = dict(metadata[idx])
        item_text = (item.get('product_name', '') + ' ' + item.get('category', '')).lower()

        # ── Category filter ────────────────────────────────────
        if is_shoe_query and not any(k in item_text for k in shoe_keywords):
            continue
        if is_bag_query and not any(k in item_text for k in bag_keywords):
            continue
        if is_trouser_query and not any(k in item_text for k in trouser_keywords):
            continue
        if is_dress_query and not any(k in item_text for k in dress_keywords):
            continue

        # ── Price filter ───────────────────────────────────────
        if max_price is not None or min_price is not None:
            price_str = item.get('price', '')
            try:
                price_val = float(price_str.replace('$', '').replace(',', '').strip())
                if max_price is not None and price_val > max_price:
                    continue
                if min_price is not None and price_val < min_price:
                    continue
            except:
                pass  # keep item if price can't be parsed

        # ── Condition filter ───────────────────────────────────
        if want_used or want_new:
            condition = item.get('condition', '').lower()
            if want_used and not any(w in condition for w in ['used', 'pre-owned', 'good', 'acceptable', 'fair']):
                continue
            if want_new and not any(w in condition for w in ['new']):
                continue

        # ── Deduplication ──────────────────────────────────────
        url = item.get('product_url', '')
        name = item.get('product_name', '')[:50]
        if url and url in seen_urls:
            continue
        if name and name in seen_names:
            continue
        seen_urls.add(url)
        seen_names.add(name)

        item["score"] = float(score)
        results.append(item)

        if len(results) >= TOP_K:
            break

    return results


# ── CRAG Step 3: Response Generation ──────────────────────────

def format_products(products: list) -> str:
    lines = []
    for i, p in enumerate(products, 1):
        lines.append(
            f"{i}. {p.get('product_name', '')}\n"
            f"   Price: {p.get('price', 'N/A')} | "
            f"Condition: {p.get('condition', '')} | "
            f"Category: {p.get('category', '')}\n"
            f"   Seller: {p.get('seller_name', '')} "
            f"({p.get('seller_feedback_percent', '')})\n"
            f"   URL: {p.get('product_url', '')}"
        )
    return "\n\n".join(lines)


def generate_response(original: str, rewritten: str, products: list, history: list) -> str:
    """Generate brief honest response based on actual retrieved products."""
    system_prompt = """You are a helpful AI shopping assistant for an eBay fashion store.
The user's search results are displayed as product cards on screen.
Write a SHORT 2-3 sentence honest response following these STRICT rules:
1. Only mention attributes the USER explicitly asked for (e.g. if they said "new shoes" only mention shoes and new condition)
2. Do NOT invent details like sizes, colors, styles, or patterns that the user did not ask for
3. Only mention price range if user asked for a specific budget
4. State how many products were found
5. Keep it friendly and under 3 sentences
6. Do NOT list individual products"""

    history_text = ""
    if history:
        history_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in history[-4:]
        )

    count = len(products)

    if count == 0:
        product_summary = "No products found matching this query."
    else:
        prices = []
        for p in products:
            price_str = p.get('price', '')
            if price_str:
                try:
                    price_val = float(price_str.replace('$', '').replace(',', '').strip())
                    prices.append(price_val)
                except:
                    pass
        if prices:
            min_p = min(prices)
            max_p = max(prices)
            product_summary = f"{count} products found. Price range: ${min_p:.2f} to ${max_p:.2f}."
        else:
            product_summary = f"{count} products found."

    import re
    budget_mentioned = bool(re.search(r'\$\d+|under\s+\d+|below\s+\d+|less than\s+\d+|budget|cheap|affordable', original.lower()))

    prompt = f"""Previous conversation:
{history_text if history_text else "None"}

User asked: {original}
{product_summary}
User mentioned budget: {budget_mentioned}

Write a short honest response. Only mention what the user asked for. Do not add details they didn't request."""

    return call_llm(prompt, system_prompt)


# ── Intent Detection ──────────────────────────────────────────

def detect_intent(user_message: str, history: list) -> str:
    """
    Detect if the user wants to search for products or just chat.
    Returns 'search' or 'conversation'.
    """
    msg = user_message.lower().strip()

    # Clear conversation patterns — short greetings/thanks only
    conversation_patterns = [
        'hi', 'hello', 'hey', 'hii', 'helo', 'hola',
        'thanks', 'thank you', 'thx', 'ty',
        'bye', 'goodbye', 'ok', 'okay', 'great', 'cool', 'nice',
        'how are you', 'what can you do', 'who are you',
        'good morning', 'good evening', 'good night',
        'yes', 'no', 'sure', 'alright', 'perfect'
    ]

    # If message is very short and matches greeting — conversation
    if msg in conversation_patterns:
        return "conversation"

    # If message is very short (1-2 words) and no product keywords — conversation
    words = msg.split()
    if len(words) <= 2 and not any(kw in msg for kw in [
        'bag', 'shoe', 'dress', 'shirt', 'pant', 'jacket', 'coat',
        'sneaker', 'boot', 'hat', 'sock', 'jean', 'skirt', 'suit',
        'cloth', 'fashion', 'wear', 'outfit', 'product', 'item',
        'buy', 'shop', 'find', 'show', 'get', 'need', 'want',
        'cheap', 'price', 'under', 'men', 'women', 'kid', 'girl', 'boy'
    ]):
        return "conversation"

    # Everything else is a search
    return "search"


def conversational_reply(user_message: str, history: list) -> str:
    """Generate a friendly conversational response without product search."""
    system = """You are a friendly AI shopping assistant for an eBay fashion store.
You help users find clothing, shoes, bags and accessories.
When users greet you or chat casually, respond warmly and briefly.
Remind them you can help find fashion products if they need.
Keep responses under 3 sentences."""

    history_text = ""
    if history:
        history_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in history[-4:]
        )

    prompt = f"""Previous conversation:
{history_text if history_text else "None"}

User: {user_message}

Respond conversationally:"""

    return call_llm(prompt, system)


# ── API Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = []


class ChatResponse(BaseModel):
    reply: str
    products: list
    rewritten_query: str


# ── Routes ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        # Step 1 — Detect intent: is this a product search or just conversation?
        intent = detect_intent(req.message, req.history or [])

        if intent == "conversation":
            # Just respond conversationally, no product search
            reply = conversational_reply(req.message, req.history or [])
            return ChatResponse(reply=reply, products=[], rewritten_query="")

        # Step 2 — CRAG: Rewrite query
        rewritten_query = rewrite_query(req.message, req.history or [])

        # Step 3 — Search products
        products = search_products(rewritten_query)

        # Step 4 — Generate response
        reply = generate_response(req.message, rewritten_query, products, req.history or [])
        return ChatResponse(reply=reply, products=products, rewritten_query=rewritten_query)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "products_indexed": index.ntotal}
