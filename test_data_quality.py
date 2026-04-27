"""
test_data_quality.py — Test if scraped data can answer real user queries
using simple keyword + field matching (no embeddings needed).

Usage:
    python test_data_quality.py
"""

import json
import re
from collections import defaultdict

DATA_FILE = "data/ebay_data.json"

# ── Test queries ────────────────────────────────────────────────
TEST_QUERIES = [
    {
        "query": "brand new black women's sneakers in small size for office",
        "filters": {
            "category_keywords": ["sneaker", "shoe"],
            "gender": "women",
            "condition_keywords": ["new"],
            "color_keywords": ["black"],
            "size_keywords": ["small", "5", "6", "7", "xs", "s"],
        }
    },
    {
        "query": "cheap men's jeans under $30",
        "filters": {
            "category_keywords": ["jean", "pant", "denim"],
            "gender": "men",
            "max_price": 30,
        }
    },
    {
        "query": "kids winter jacket for boys",
        "filters": {
            "category_keywords": ["jacket", "coat"],
            "gender_keywords": ["boy", "kid", "child"],
        }
    },
    {
        "query": "women's red handbag leather",
        "filters": {
            "category_keywords": ["bag", "handbag", "purse"],
            "gender": "women",
            "color_keywords": ["red"],
            "material_keywords": ["leather"],
        }
    },
    {
        "query": "men's formal suit for wedding",
        "filters": {
            "category_keywords": ["suit", "formal", "tuxedo"],
            "gender": "men",
        }
    },
]


def extract_price(price_str):
    if not price_str:
        return None
    m = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
    return float(m.group()) if m else None


def get_all_text(item):
    """Combine all searchable text from an item."""
    parts = [
        item.get("product_name", ""),
        item.get("category", ""),
        item.get("condition", ""),
        item.get("seller_description", ""),
        " ".join(f"{k} {v}" for k, v in item.get("item_specifics", {}).items()),
    ]
    return " ".join(parts).lower()


def matches_query(item, filters):
    text = get_all_text(item)
    specifics = {k.lower(): v.lower() for k, v in item.get("item_specifics", {}).items()}

    # Category keywords
    if "category_keywords" in filters:
        if not any(kw in text for kw in filters["category_keywords"]):
            return False, "category"

    # Gender
    if "gender" in filters:
        g = filters["gender"]
        cat = item.get("category", "").lower()
        name = item.get("product_name", "").lower()
        if g == "women" and not any(w in cat + name for w in ["women", "woman", "female", "ladies", "girl"]):
            return False, "gender"
        if g == "men" and not any(w in cat + name for w in ["men", "man", "male", "boy", "guys"]):
            return False, "gender"

    # Gender keywords (flexible)
    if "gender_keywords" in filters:
        if not any(kw in text for kw in filters["gender_keywords"]):
            return False, "gender_keywords"

    # Condition
    if "condition_keywords" in filters:
        condition = item.get("condition", "").lower()
        if not any(kw in condition for kw in filters["condition_keywords"]):
            return False, "condition"

    # Color
    if "color_keywords" in filters:
        color_fields = [
            specifics.get("color", ""),
            specifics.get("colour", ""),
            item.get("product_name", "").lower(),
            item.get("seller_description", "").lower()[:200],
        ]
        color_text = " ".join(color_fields)
        if not any(kw in color_text for kw in filters["color_keywords"]):
            return False, "color"

    # Size
    if "size_keywords" in filters:
        size_fields = [
            specifics.get("size", ""),
            specifics.get("shoe size", ""),
            specifics.get("us shoe size", ""),
            specifics.get("size type", ""),
            item.get("product_name", "").lower(),
        ]
        size_text = " ".join(size_fields)
        if not any(kw in size_text for kw in filters["size_keywords"]):
            return False, "size"

    # Material
    if "material_keywords" in filters:
        mat_fields = [
            specifics.get("material", ""),
            specifics.get("upper material", ""),
            specifics.get("fabric type", ""),
            item.get("product_name", "").lower(),
        ]
        mat_text = " ".join(mat_fields)
        if not any(kw in mat_text for kw in filters["material_keywords"]):
            return False, "material"

    # Max price
    if "max_price" in filters:
        price = extract_price(item.get("price", ""))
        if price is None or price > filters["max_price"]:
            return False, "price"

    return True, None


def analyze_field_coverage(data):
    """Check what % of items have each important field."""
    fields = {
        "product_name": 0,
        "price": 0,
        "condition": 0,
        "seller_name": 0,
        "image_urls": 0,
        "item_specifics": 0,
        "color_in_specifics": 0,
        "size_in_specifics": 0,
        "brand_in_specifics": 0,
        "material_in_specifics": 0,
        "seller_description": 0,
    }

    for item in data:
        if item.get("product_name"): fields["product_name"] += 1
        if item.get("price"): fields["price"] += 1
        if item.get("condition"): fields["condition"] += 1
        if item.get("seller_name"): fields["seller_name"] += 1
        if item.get("image_urls"): fields["image_urls"] += 1
        if item.get("item_specifics"): fields["item_specifics"] += 1
        if item.get("seller_description"): fields["seller_description"] += 1

        specs = {k.lower(): v for k, v in item.get("item_specifics", {}).items()}
        if any(k in specs for k in ["color", "colour"]): fields["color_in_specifics"] += 1
        if any(k in specs for k in ["size", "shoe size", "us shoe size", "size type"]): fields["size_in_specifics"] += 1
        if "brand" in specs: fields["brand_in_specifics"] += 1
        if any(k in specs for k in ["material", "fabric type", "upper material"]): fields["material_in_specifics"] += 1

    total = len(data)
    print("\n" + "="*60)
    print("  FIELD COVERAGE ANALYSIS")
    print("="*60)
    for field, count in fields.items():
        pct = count / total * 100
        bar = "█" * int(pct / 5)
        status = "✓" if pct > 70 else ("⚠" if pct > 30 else "✗")
        print(f"  {status} {field:<30} {bar:<20} {pct:5.1f}%")


def run_tests(data):
    print("\n" + "="*60)
    print("  QUERY MATCHING TESTS")
    print("="*60)

    for test in TEST_QUERIES:
        print(f"\n  Query: \"{test['query']}\"")
        print(f"  {'-'*55}")

        matched = []
        fail_reasons = defaultdict(int)

        for item in data:
            ok, reason = matches_query(item, test["filters"])
            if ok:
                matched.append(item)
            else:
                fail_reasons[reason] += 1

        print(f"  ✓ Matched: {len(matched)} items")

        if matched:
            print(f"  Top 3 results:")
            for item in matched[:3]:
                specs = item.get("item_specifics", {})
                color = specs.get("Color", specs.get("Colour", "N/A"))
                size  = specs.get("Size", specs.get("Shoe Size", specs.get("US Shoe Size", "N/A")))
                print(f"    • {item['product_name'][:55]}")
                print(f"      Price: {item.get('price','N/A')} | Condition: {item.get('condition','N/A')}")
                print(f"      Color: {color} | Size: {size}")
                print(f"      Category: {item.get('category','N/A')}")
        else:
            print(f"  ✗ No matches found!")
            print(f"  Fail reasons: {dict(fail_reasons)}")

        # Show what's missing
        if len(matched) < 5:
            print(f"  ⚠ Low results — fail breakdown: {dict(sorted(fail_reasons.items(), key=lambda x: -x[1])[:3])}")


def category_breakdown(data):
    cats = defaultdict(int)
    for item in data:
        cats[item.get("category", "Unknown")] += 1

    print("\n" + "="*60)
    print("  CATEGORY BREAKDOWN")
    print("="*60)
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        bar = "█" * min(count // 20, 25)
        print(f"  {cat:<40} {bar} {count}")


if __name__ == "__main__":
    print("Loading data...")
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total items: {len(data)}")

    category_breakdown(data)
    analyze_field_coverage(data)
    run_tests(data)

    print("\n" + "="*60)
    print("  DONE")
    print("="*60)
