"""
config.py — eBay Fashion Scraper Configuration
Target: ~20,000 products across Men, Women, Kids clothing & shoes
Site: eBay USA (ebay.com)
Conditions: All (New + Used + Refurbished)
"""

# ═══════════════════════════════════════════════════════════════
#  MAIN SETTINGS
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    # eBay USA base search URL
    "base_url": "https://www.ebay.com/sch/i.html",

    # Output files
    "output_json":    "ebay_data.json",
    "output_csv":     "ebay_data.csv",
    "progress_file":  "progress.json",
    "patch_progress": "patch_progress.json",

    # How many products to collect per category
    # 40 categories × 500 = 20,000 total
    "target_per_cat": 500,

    # Pagination
    "max_pages":      50,    # max pages to go through per keyword
    "items_per_page": 48,    # eBay default is 48

    # Delays between requests (seconds) — mimics human browsing
    "delay_min":      3.0,   # between pages
    "delay_max":      7.0,
    "item_delay_min": 2.0,   # between individual product pages
    "item_delay_max": 5.0,

    # Browser settings
    "headless":       True,  # True = invisible browser (recommended for EC2)
    "page_timeout":   30,    # seconds before page load gives up
}


# ═══════════════════════════════════════════════════════════════
#  REQUIRED FIELDS
#  Items missing ANY of these will be re-scraped
# ═══════════════════════════════════════════════════════════════

REQUIRED_FIELDS = [
    "product_name",
    "price",
    "condition",
    "seller_name",
]


# ═══════════════════════════════════════════════════════════════
#  SUBCATEGORIES
#  Format: "Category Label": (eBay_category_id, [keywords])
#
#  eBay Category IDs used:
#   15724  = Women's Clothing
#   1059   = Men's Clothing
#   57988  = Girls' Clothing (Kids)
#   57989  = Boys' Clothing (Kids)
#   3034   = Women's Shoes
#   93427  = Men's Shoes
#   57929  = Girls' Shoes
#   57930  = Boys' Shoes
#   169291 = Women's Bags & Handbags
#   169285 = Men's Bags
#   57929  = Kids' Shoes
# ═══════════════════════════════════════════════════════════════

SUBCATEGORIES = {

    # ─────────────────────────────────────────
    #  WOMEN'S CLOTHING
    # ─────────────────────────────────────────
    "Women's Dresses": (
        15724,
        ["women dress", "womens maxi dress", "womens mini dress",
         "womens casual dress", "womens formal dress"]
    ),
    "Women's Tops & Blouses": (
        15724,
        ["womens blouse", "womens top shirt", "womens t-shirt",
         "womens crop top", "womens tank top"]
    ),
    "Women's Pants & Jeans": (
        15724,
        ["womens jeans", "womens pants", "womens trousers",
         "womens leggings", "womens joggers"]
    ),
    "Women's Skirts": (
        15724,
        ["womens skirt", "womens midi skirt", "womens mini skirt",
         "womens maxi skirt", "womens pleated skirt"]
    ),
    "Women's Jackets & Coats": (
        15724,
        ["womens jacket", "womens coat", "womens blazer",
         "womens winter coat", "womens puffer jacket"]
    ),
    "Women's Sweaters & Hoodies": (
        15724,
        ["womens sweater", "womens hoodie", "womens sweatshirt",
         "womens cardigan", "womens pullover"]
    ),
    "Women's Activewear": (
        15724,
        ["womens activewear", "womens yoga pants", "womens sports bra",
         "womens gym outfit", "womens workout set"]
    ),
    "Women's Swimwear": (
        15724,
        ["womens swimsuit", "womens bikini", "womens one piece swimsuit",
         "womens swimwear", "womens bathing suit"]
    ),

    # ─────────────────────────────────────────
    #  MEN'S CLOTHING
    # ─────────────────────────────────────────
    "Men's Shirts": (
        1059,
        ["mens shirt", "mens dress shirt", "mens polo shirt",
         "mens casual shirt", "mens button down shirt"]
    ),
    "Men's T-Shirts": (
        1059,
        ["mens t-shirt", "mens graphic tee", "mens plain tshirt",
         "mens crew neck tshirt", "mens v-neck tshirt"]
    ),
    "Men's Pants & Jeans": (
        1059,
        ["mens jeans", "mens pants", "mens trousers",
         "mens chinos", "mens cargo pants"]
    ),
    "Men's Shorts": (
        1059,
        ["mens shorts", "mens cargo shorts", "mens athletic shorts",
         "mens board shorts", "mens chino shorts"]
    ),
    "Men's Jackets & Coats": (
        1059,
        ["mens jacket", "mens coat", "mens blazer",
         "mens winter jacket", "mens puffer jacket"]
    ),
    "Men's Sweaters & Hoodies": (
        1059,
        ["mens hoodie", "mens sweater", "mens sweatshirt",
         "mens cardigan", "mens zip up hoodie"]
    ),
    "Men's Suits": (
        1059,
        ["mens suit", "mens dress suit", "mens formal suit",
         "mens blazer suit", "mens tuxedo"]
    ),
    "Men's Activewear": (
        1059,
        ["mens activewear", "mens gym shorts", "mens workout shirt",
         "mens track pants", "mens athletic wear"]
    ),

    # ─────────────────────────────────────────
    #  WOMEN'S SHOES
    # ─────────────────────────────────────────
    "Women's Heels": (
        3034,
        ["womens heels", "womens high heels", "womens stiletto",
         "womens block heels", "womens pumps"]
    ),
    "Women's Sneakers": (
        3034,
        ["womens sneakers", "womens running shoes", "womens athletic shoes",
         "womens casual sneakers", "womens white sneakers"]
    ),
    "Women's Boots": (
        3034,
        ["womens boots", "womens ankle boots", "womens knee high boots",
         "womens winter boots", "womens Chelsea boots"]
    ),
    "Women's Sandals & Flats": (
        3034,
        ["womens sandals", "womens flat shoes", "womens ballet flats",
         "womens flip flops", "womens slide sandals"]
    ),
    "Women's Loafers & Slip-ons": (
        3034,
        ["womens loafers", "womens slip on shoes", "womens mules",
         "womens espadrilles", "womens platform loafers"]
    ),

    # ─────────────────────────────────────────
    #  MEN'S SHOES
    # ─────────────────────────────────────────
    "Men's Sneakers": (
        93427,
        ["mens sneakers", "mens running shoes", "mens athletic shoes",
         "mens casual sneakers", "mens white sneakers"]
    ),
    "Men's Boots": (
        93427,
        ["mens boots", "mens ankle boots", "mens work boots",
         "mens Chelsea boots", "mens winter boots"]
    ),
    "Men's Dress Shoes": (
        93427,
        ["mens dress shoes", "mens oxford shoes", "mens loafers",
         "mens formal shoes", "mens leather shoes"]
    ),
    "Men's Sandals & Slippers": (
        93427,
        ["mens sandals", "mens slippers", "mens flip flops",
         "mens slide sandals", "mens sport sandals"]
    ),

    # ─────────────────────────────────────────
    #  KIDS - GIRLS CLOTHING
    # ─────────────────────────────────────────
    "Girls' Dresses": (
        57988,
        ["girls dress", "girls party dress", "girls casual dress",
         "girls sundress", "girls floral dress"]
    ),
    "Girls' Tops & T-Shirts": (
        57988,
        ["girls top", "girls t-shirt", "girls blouse",
         "girls graphic tee", "girls tank top"]
    ),
    "Girls' Pants & Jeans": (
        57988,
        ["girls jeans", "girls pants", "girls leggings",
         "girls trousers", "girls joggers"]
    ),
    "Girls' Jackets & Coats": (
        57988,
        ["girls jacket", "girls coat", "girls hoodie",
         "girls puffer jacket", "girls winter coat"]
    ),

    # ─────────────────────────────────────────
    #  KIDS - BOYS CLOTHING
    # ─────────────────────────────────────────
    "Boys' Shirts & T-Shirts": (
        57989,
        ["boys t-shirt", "boys shirt", "boys polo shirt",
         "boys graphic tee", "boys dress shirt"]
    ),
    "Boys' Pants & Jeans": (
        57989,
        ["boys jeans", "boys pants", "boys shorts",
         "boys trousers", "boys cargo pants"]
    ),
    "Boys' Jackets & Hoodies": (
        57989,
        ["boys jacket", "boys hoodie", "boys sweatshirt",
         "boys coat", "boys puffer jacket"]
    ),
    "Boys' Suits & Formal": (
        57989,
        ["boys suit", "boys formal wear", "boys dress pants",
         "boys blazer", "boys tuxedo"]
    ),

    # ─────────────────────────────────────────
    #  KIDS - SHOES
    # ─────────────────────────────────────────
    "Girls' Shoes": (
        57929,
        ["girls sneakers", "girls shoes", "girls boots",
         "girls sandals", "girls school shoes"]
    ),
    "Boys' Shoes": (
        57930,
        ["boys sneakers", "boys shoes", "boys boots",
         "boys sandals", "boys school shoes"]
    ),

    # ─────────────────────────────────────────
    #  BAGS & ACCESSORIES
    # ─────────────────────────────────────────
    "Women's Handbags": (
        169291,
        ["womens handbag", "womens purse", "womens tote bag",
         "womens crossbody bag", "womens shoulder bag"]
    ),
    "Women's Backpacks": (
        169291,
        ["womens backpack", "womens mini backpack", "womens leather backpack",
         "womens school backpack", "womens travel backpack"]
    ),
    "Men's Bags": (
        169285,
        ["mens bag", "mens backpack", "mens messenger bag",
         "mens laptop bag", "mens leather bag"]
    ),
    "Kids' Backpacks": (
        260220,
        ["kids backpack", "girls school backpack", "boys school backpack",
         "children backpack", "kids cartoon backpack"]
    ),
}


# ═══════════════════════════════════════════════════════════════
#  CUSTOM URLS (optional)
#  Use these if you want to scrape a SPECIFIC eBay search URL
#  directly instead of building it from category ID + keyword.
#  Leave empty if not needed.
# ═══════════════════════════════════════════════════════════════

CUSTOM_URLS = {
    # Example (uncomment to use):
    # "Women's Designer Dresses": "https://www.ebay.com/sch/i.html?_nkw=womens+designer+dress&_sop=10",
}
