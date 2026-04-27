"""
data_quality_monitor.py — Real-time data quality monitor for ebay_data.json

Watches the data file and reports quality metrics as scraping progresses.

Usage:
    python data_quality_monitor.py          # one-time report
    python data_quality_monitor.py --watch  # refresh every 30s
"""

import json
import re
import sys
import time
import os
from collections import defaultdict

DATA_FILE = "data/ebay_data.json"

TARGET_CATS = [
    "Women's Dresses", "Women's Tops & Blouses", "Women's Pants & Jeans",
    "Women's Skirts", "Women's Jackets & Coats", "Women's Sweaters & Hoodies",
    "Women's Activewear", "Women's Swimwear",
    "Men's Shirts", "Men's T-Shirts", "Men's Pants & Jeans", "Men's Shorts",
    "Men's Jackets & Coats", "Men's Sweaters & Hoodies", "Men's Suits", "Men's Activewear",
    "Women's Heels", "Women's Sneakers", "Women's Boots", "Women's Sandals & Flats",
    "Women's Loafers & Slip-ons", "Men's Sneakers", "Men's Boots", "Men's Dress Shoes",
    "Men's Sandals & Slippers", "Girls' Dresses", "Girls' Tops & T-Shirts",
    "Girls' Pants & Jeans", "Girls' Jackets & Coats", "Boys' Shirts & T-Shirts",
    "Boys' Pants & Jeans", "Boys' Jackets & Hoodies", "Boys' Suits & Formal",
    "Girls' Shoes", "Boys' Shoes", "Women's Handbags", "Women's Backpacks",
    "Men's Bags", "Kids' Backpacks"
]

QUALITY_FIELDS = [
    ("product_name",    "Product Name"),
    ("price",           "Price"),
    ("condition",       "Condition"),
    ("seller_name",     "Seller Name"),
    ("image_urls",      "Images"),
    ("item_specifics",  "Item Specifics"),
    ("seller_description", "Description"),
]

SPEC_FIELDS = [
    (["Color", "Colour"],                           "Color"),
    (["Size", "Shoe Size", "Us Shoe Size"],         "Size"),
    (["Brand"],                                     "Brand"),
    (["Material", "Fabric Type", "Upper Material"], "Material"),
    (["Style"],                                     "Style"),
    (["Department", "Gender"],                      "Gender/Dept"),
]


def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"File not found: {DATA_FILE}")
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def extract_price(price_str):
    if not price_str:
        return None
    m = re.search(r'[\d,]+\.?\d*', str(price_str).replace(',', ''))
    return float(m.group()) if m else None


def report(data):
    total = len(data)
    if total == 0:
        print("No data found.")
        return

    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 70)
    print(f"  eBay Data Quality Monitor")
    print(f"  File: {DATA_FILE}")
    print(f"  Total items: {total} / 19,500 ({total/195:.1f}%)")
    print("=" * 70)

    # ── Category breakdown ──────────────────────────────────────
    cats = defaultdict(int)
    for item in data:
        cats[item.get("category", "Unknown")] += 1

    print("\n  CATEGORY PROGRESS")
    print(f"  {'Category':<40} {'Have':>5}  {'Target':>6}  Status")
    print("  " + "─" * 62)
    done_count = 0
    for cat in TARGET_CATS:
        count = cats.get(cat, 0)
        if count >= 500:
            status = "✓ DONE"
            done_count += 1
        elif count > 0:
            pct = count / 500 * 100
            bar = "█" * int(pct / 10)
            status = f"▶ {bar:<10} {pct:.0f}%"
        else:
            status = "✗ MISSING"
        print(f"  {cat:<40} {count:>5}  {500:>6}  {status}")

    print(f"\n  Complete: {done_count}/{len(TARGET_CATS)} categories")

    # ── Field coverage ──────────────────────────────────────────
    print("\n  FIELD COVERAGE")
    print(f"  {'Field':<30} {'Count':>7}  {'%':>6}  Status")
    print("  " + "─" * 55)
    for field, label in QUALITY_FIELDS:
        count = sum(1 for item in data if item.get(field))
        pct = count / total * 100
        status = "✓" if pct >= 90 else ("⚠" if pct >= 60 else "✗")
        bar = "█" * int(pct / 10)
        print(f"  {label:<30} {count:>7}  {pct:>5.1f}%  {status} {bar}")

    # ── Item specifics coverage ─────────────────────────────────
    print("\n  ITEM SPECIFICS COVERAGE")
    print(f"  {'Field':<30} {'Count':>7}  {'%':>6}  Status")
    print("  " + "─" * 55)
    for keys, label in SPEC_FIELDS:
        count = sum(
            1 for item in data
            if any(k in item.get("item_specifics", {}) for k in keys)
        )
        pct = count / total * 100
        status = "✓" if pct >= 80 else ("⚠" if pct >= 50 else "✗")
        bar = "█" * int(pct / 10)
        print(f"  {label:<30} {count:>7}  {pct:>5.1f}%  {status} {bar}")

    # ── Quality score distribution ──────────────────────────────
    scores = [item.get("quality_score", 0) for item in data]
    if any(s > 0 for s in scores):
        avg = sum(scores) / len(scores)
        high = sum(1 for s in scores if s >= 80)
        med  = sum(1 for s in scores if 50 <= s < 80)
        low  = sum(1 for s in scores if s < 50)
        print(f"\n  QUALITY SCORE DISTRIBUTION (avg: {avg:.1f}/100)")
        print(f"  High (80-100): {high:>6} ({high/total*100:.1f}%)")
        print(f"  Med  (50-79):  {med:>6} ({med/total*100:.1f}%)")
        print(f"  Low  (0-49):   {low:>6} ({low/total*100:.1f}%)")

    # ── Price distribution ──────────────────────────────────────
    prices = [extract_price(item.get("price")) for item in data]
    prices = [p for p in prices if p is not None]
    if prices:
        print(f"\n  PRICE DISTRIBUTION")
        print(f"  Min: ${min(prices):.2f}  |  Max: ${max(prices):.2f}  |  Avg: ${sum(prices)/len(prices):.2f}")
        ranges = [
            ("Under $20",    sum(1 for p in prices if p < 20)),
            ("$20 - $50",    sum(1 for p in prices if 20 <= p < 50)),
            ("$50 - $100",   sum(1 for p in prices if 50 <= p < 100)),
            ("$100 - $200",  sum(1 for p in prices if 100 <= p < 200)),
            ("Over $200",    sum(1 for p in prices if p >= 200)),
        ]
        for label, count in ranges:
            bar = "█" * min(count // 100, 20)
            print(f"  {label:<15} {count:>6}  {bar}")

    # ── Condition breakdown ─────────────────────────────────────
    conditions = defaultdict(int)
    for item in data:
        cond = item.get("condition_normalized") or item.get("condition", "Unknown")
        conditions[cond] += 1
    print(f"\n  CONDITION BREAKDOWN")
    for cond, count in sorted(conditions.items(), key=lambda x: -x[1])[:6]:
        bar = "█" * min(count // 100, 20)
        print(f"  {cond:<30} {count:>6}  {bar}")

    # ── Issues ──────────────────────────────────────────────────
    issues = []
    no_color    = sum(1 for item in data if not any(k in item.get("item_specifics", {}) for k in ["Color", "Colour"]))
    no_size     = sum(1 for item in data if not any(k in item.get("item_specifics", {}) for k in ["Size", "Shoe Size", "Us Shoe Size"]))
    no_brand    = sum(1 for item in data if "Brand" not in item.get("item_specifics", {}))
    no_images   = sum(1 for item in data if not item.get("image_urls"))
    low_quality = sum(1 for item in data if item.get("quality_score", 100) < 50)

    if no_color > total * 0.1:    issues.append(f"  ⚠ {no_color} items missing Color in specifics")
    if no_size > total * 0.1:     issues.append(f"  ⚠ {no_size} items missing Size in specifics")
    if no_brand > total * 0.2:    issues.append(f"  ⚠ {no_brand} items missing Brand in specifics")
    if no_images > 0:             issues.append(f"  ⚠ {no_images} items missing images")
    if low_quality > total * 0.1: issues.append(f"  ⚠ {low_quality} items with quality score < 50")

    if issues:
        print(f"\n  ISSUES DETECTED")
        for issue in issues:
            print(issue)
    else:
        print(f"\n  ✓ No major issues detected")

    # ── Category-Product alignment check ───────────────────────
    print(f"\n  CATEGORY ALIGNMENT CHECK")
    print(f"  Verifying products match their assigned category...")
    print(f"  {'Category':<40} {'Total':>6}  {'Mismatch':>8}  {'%':>6}")
    print("  " + "─" * 65)

    # Keywords that should appear in product name or specifics for each category group
    CATEGORY_RULES = {
        "women": {
            "cats": [c for c in TARGET_CATS if c.startswith("Women's")],
            "expected_keywords": ["women", "woman", "female", "ladies", "girl", "her"],
            "forbidden_keywords": ["men's", "boys", "mens "],
        },
        "men": {
            "cats": [c for c in TARGET_CATS if c.startswith("Men's")],
            "expected_keywords": ["men", "man", "male", "guy", "his"],
            "forbidden_keywords": ["women's", "girls", "womens "],
        },
        "girls": {
            "cats": [c for c in TARGET_CATS if c.startswith("Girls'")],
            "expected_keywords": ["girl", "girls", "kids", "children", "child"],
            "forbidden_keywords": [],
        },
        "boys": {
            "cats": [c for c in TARGET_CATS if c.startswith("Boys'")],
            "expected_keywords": ["boy", "boys", "kids", "children", "child"],
            "forbidden_keywords": [],
        },
    }

    total_mismatches = 0
    mismatch_examples = []

    for group, rules in CATEGORY_RULES.items():
        group_items = [item for item in data if item.get("category") in rules["cats"]]
        if not group_items:
            continue

        mismatches = []
        for item in group_items:
            # Build searchable text
            name = item.get("product_name", "").lower()
            specs = " ".join(f"{k} {v}" for k, v in item.get("item_specifics", {}).items()).lower()
            desc = item.get("seller_description", "").lower()[:200]
            cat = item.get("category", "").lower()
            all_text = f"{name} {specs} {cat}"

            # Check if forbidden keywords appear in product name
            has_forbidden = any(kw in name for kw in rules["forbidden_keywords"])
            if has_forbidden:
                mismatches.append(item)

        pct = len(mismatches) / len(group_items) * 100 if group_items else 0
        status = "✓" if pct < 2 else ("⚠" if pct < 10 else "✗")
        print(f"  {status} {group.upper():<38} {len(group_items):>6}  {len(mismatches):>8}  {pct:>5.1f}%")

        total_mismatches += len(mismatches)
        if mismatches:
            mismatch_examples.extend(mismatches[:2])

    if mismatch_examples:
        print(f"\n  Sample mismatched items:")
        for item in mismatch_examples[:4]:
            print(f"    • [{item.get('category')}] {item.get('product_name','')[:55]}")
    elif total_mismatches == 0:
        print(f"\n  ✓ All products match their categories correctly")

    print(f"\n  Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    watch_mode = "--watch" in sys.argv

    if watch_mode:
        print("Watching data quality (Ctrl+C to stop)...")
        try:
            while True:
                data = load_data()
                report(data)
                print("\n  Refreshing in 30s...")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        data = load_data()
        report(data)
