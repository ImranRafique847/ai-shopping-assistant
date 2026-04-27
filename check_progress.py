import json
from collections import defaultdict

with open('data/ebay_data.json', encoding='utf-8') as f:
    data = json.load(f)

cats = defaultdict(int)
for item in data:
    cats[item.get('category', 'Unknown')] += 1

target_cats = [
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

total = len(data)
target_total = 19500

print("=" * 70)
print(f"  eBay Scraping Progress Report")
print(f"  Total: {total} / {target_total} ({total/target_total*100:.1f}%)")
print("=" * 70)
print(f"\n{'Category':<40} {'Have':>6}  {'%':>6}  {'Bar':<20}  Status")
print('-' * 80)

done = partial = missing = 0
for cat in target_cats:
    count = cats.get(cat, 0)
    pct = count / 500 * 100
    bar = '█' * int(pct / 5)
    if count >= 500:
        status = '✓ DONE'
        done += 1
    elif count > 0:
        status = f'▶ {500-count} left'
        partial += 1
    else:
        status = '✗ MISSING'
        missing += 1
    print(f"{cat:<40} {count:>6}  {pct:>5.1f}%  {bar:<20}  {status}")

print()
print(f"  ✓ Complete : {done}/{len(target_cats)} categories")
print(f"  ▶ Partial  : {partial}/{len(target_cats)} categories")
print(f"  ✗ Missing  : {missing}/{len(target_cats)} categories")
print(f"\n  Overall progress: {total/target_total*100:.1f}%")
print("=" * 70)
