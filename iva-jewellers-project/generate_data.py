"""
Synthetic data generator - "Iva Jewellers" (FICTIONAL), 3 stores in the GTA.
Period: 2023-01-01 to 2026-09-30. Currency: CAD.

Simulates: daily gold rate, customer invoices by segment & season, store-level
inventory with weekly reorder reviews, supplier lead times / late deliveries,
stockouts (missed requests), returns/exchanges, monthly opex, FY2026 budget.
A few realistic data-quality issues are injected into the raw exports on purpose.
All names, numbers and suppliers are invented. Not real business data.
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import os, sys

rng = np.random.default_rng(2026)
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
os.makedirs(OUT, exist_ok=True)

START, END = date(2023, 1, 1), date(2026, 9, 30)
DATES = [START + timedelta(d) for d in range((END - START).days + 1)]

# ------------------------------------------------------------------ gold rate
# Simulated 24K gold price in CAD per gram, loosely following the market trend.
anchors = [(date(2023,1,1),81),(date(2023,5,1),87),(date(2023,10,1),83),(date(2024,1,1),89),
           (date(2024,4,15),101),(date(2024,10,31),119),(date(2025,1,1),121),(date(2025,4,20),146),
           (date(2025,8,1),148),(date(2025,10,15),181),(date(2026,1,1),186),(date(2026,3,1),198),
           (date(2026,6,1),192),(date(2026,9,30),201)]
ax = np.array([(a - START).days for a, _ in anchors]); ay = np.log([v for _, v in anchors])
base = np.interp(np.arange(len(DATES)), ax, ay)
noise = np.zeros(len(DATES)); e = 0
for i in range(len(DATES)):
    e = 0.93 * e + rng.normal(0, 0.006); noise[i] = e
gold24 = np.round(np.exp(base + noise), 2)
GOLD = {d: g for d, g in zip(DATES, gold24)}
SILVER = {d: round(g / 85, 3) for d, g in zip(DATES, gold24)}  # simple ratio
gold_df = pd.DataFrame({"rate_date": DATES, "gold_24k_cad_per_g": gold24,
                        "gold_22k_cad_per_g": np.round(gold24 * 0.916, 2),
                        "gold_18k_cad_per_g": np.round(gold24 * 0.750, 2),
                        "silver_cad_per_g": [SILVER[d] for d in DATES]})
G0 = gold24[:365].mean()

# ------------------------------------------------------------------ stores
stores = pd.DataFrame([
    ["ST01", "Iva Brampton", "Brampton", "2019-05-01", 7, 19500, 1.30],
    ["ST02", "Iva Mississauga", "Mississauga", "2021-08-01", 6, 16500, 1.00],
    ["ST03", "Iva Toronto - Gerrard St", "Toronto", "2024-03-01", 5, 12500, 0.85],
], columns=["store_id", "store_name", "city", "open_date", "headcount", "monthly_rent_cad", "size_factor"])
STORE_IDS = list(stores.store_id)
SF = dict(zip(stores.store_id, stores.size_factor))
OPEN = {r.store_id: pd.Timestamp(r.open_date).date() for r in stores.itertuples()}

def store_ramp(s, d):
    if d < OPEN[s]: return 0.0
    m = (d - OPEN[s]).days / 30.4
    return min(1.0, 0.45 + 0.55 * m / 10) if s == "ST03" else 1.0

# ------------------------------------------------------------------ suppliers
suppliers = pd.DataFrame([
    ["SUP01", "Zaveri Ornaments Pvt (Mumbai)", "India", 0.065, 2.6, 38, 0.78],
    ["SUP02", "Coimbatore Chain Works", "India", 0.035, 2.2, 32, 0.90],
    ["SUP03", "Toronto Gold Craft Inc.", "Canada", 0.040, 4.2, 10, 0.95],
    ["SUP04", "Rajkot Temple Jewels", "India", 0.070, 3.0, 45, 0.70],
    ["SUP05", "Kolkata Bangle House", "India", 0.050, 2.5, 40, 0.84],
    ["SUP06", "GTA Diamond Studio", "Canada", 0.030, 5.5, 14, 0.92],
    ["SUP07", "Maple Bullion Supply", "Canada", 0.015, 0.8, 4, 0.98],
    ["SUP08", "Jaipur Silver Arts", "India", 0.000, 0.0, 42, 0.82],
], columns=["supplier_id", "supplier_name", "country", "gold_wastage_pct",
            "labour_cad_per_g", "standard_lead_time_days", "on_time_rate_target"])
SUP = suppliers.set_index("supplier_id").to_dict("index")
# note: the 'on_time_rate_target' column is internal to the simulation and dropped on export

# ------------------------------------------------------------------ products
CATS = {
 # cat: kind, purity, weight range, VA% (making charge to customer), suppliers, sizes, n_designs, names
 "Gold Chains":      ("gold", .916, (8, 22),  (.10, .14), ["SUP02", "SUP03"], ["18in", "20in", "22in", "24in"], 5,
                      ["Rope", "Box Link", "Figaro", "Singapore", "Cable"]),
 "Gold Bangles":     ("gold", .916, (14, 32), (.14, .18), ["SUP05", "SUP01"], ["2.4", "2.6", "2.8"], 4,
                      ["Plain Kada", "Filigree", "Kangan Twist", "Meenakari"]),
 "Gold Rings":       ("gold", .916, (3, 7),   (.15, .20), ["SUP03", "SUP01"], ["5", "6", "7", "8", "9"], 6,
                      ["Solitaire Look", "Leaf Band", "Floral", "Signet", "Twist Band", "Minimal Dome"]),
 "Gold Earrings":    ("gold", .916, (4, 12),  (.16, .22), ["SUP01", "SUP03"], [None], 10,
                      ["Jhumka Classic", "Chandbali", "Stud Lotus", "Hoop Small", "Hoop Large", "Drop Pearl",
                       "Kundan Stud", "Minimal Bar", "Minimal Huggie", "Temple Jhumka"]),
 "Necklace Sets":    ("gold", .916, (40, 85), (.14, .18), ["SUP01", "SUP04"], [None], 8,
                      ["Bridal Haar", "Rani Haar", "Choker Kundan", "Lakshmi Kasu", "Antique Mango",
                       "Temple Haram", "Temple Choker", "Light Wedding Set"]),
 "Mangalsutra":      ("gold", .916, (10, 22), (.12, .15), ["SUP01", "SUP02"], [None], 6,
                      ["Traditional Vati", "Diamond Pendant MS", "Short Modern", "Long Classic",
                       "Minimal Chain MS", "Double Line"]),
 "Gold Coins":       ("coin", .999, (5, 20),  (.03, .05), ["SUP07"], [None], 3, ["5g Coin", "10g Coin", "20g Bar"]),
 "Diamond Rings":    ("diamond", .750, (3, 5), (.18, .22), ["SUP06"], ["5", "6", "7", "8"], 4,
                      ["Solitaire 0.5ct", "Halo Ring", "Eternity Band", "Cluster Ring"]),
 "Diamond Earrings": ("diamond", .750, (2, 5), (.18, .22), ["SUP06"], [None], 6,
                      ["Solitaire Studs", "Halo Studs", "Drop Diamond", "Huggie Diamond", "Floral Cluster",
                       "Minimal Diamond Bar"]),
 "Silver Jewellery": ("silver", .925, (8, 60), (0, 0), ["SUP08"], [None], 12,
                      ["Anklet Pair", "Toe Rings", "Oxidised Jhumka", "Silver Kada", "Pooja Thali",
                       "Kids Bracelet", "Rakhi Set", "Silver Coin 10g", "Oxidised Necklace", "Charm Bracelet",
                       "Silver Idol Ganesh", "Minimal Silver Chain"]),
}
COLLECTION = {}  # design name -> (collection, launch, planned_pop, actual_pop)
for n in ["Minimal Dome", "Minimal Bar", "Minimal Huggie", "Minimal Chain MS", "Minimal Diamond Bar",
          "Minimal Silver Chain", "Light Wedding Set"]:
    COLLECTION[n] = ("Minimal Daily Wear", date(2025, 3, 1), 0.9, 1.9)
for n in ["Temple Jhumka", "Temple Haram", "Temple Choker"]:
    COLLECTION[n] = ("Temple Heritage", date(2025, 9, 1), 1.3, 0.35)
for n in ["Meenakari", "Kundan Stud", "Choker Kundan"]:
    COLLECTION[n] = ("Festive Kundan 2024", date(2024, 9, 15), 1.0, 1.1)

SIZE_ACTUAL = {"5": .10, "6": .23, "7": .33, "8": .23, "9": .11,
               "18in": .30, "20in": .35, "22in": .22, "24in": .13,
               "2.4": .30, "2.6": .45, "2.8": .25}

prod_rows = []
pid = 0
for cat, (kind, purity, wr, va, sups, sizes, nd, names) in CATS.items():
    for di, dname in enumerate(names[:nd]):
        coll, launch, ppop, apop = COLLECTION.get(dname, ("Core", date(2022, 1, 1), 1.0, 1.0))
        apop *= rng.uniform(0.6, 1.5) if coll == "Core" else 1.0
        w = round(rng.uniform(*wr), 1)
        if cat == "Gold Coins": w = [5, 10, 20][di]
        if coll == "Minimal Daily Wear": w = round(w * 0.6, 1)
        vapct = round(rng.uniform(*va), 3) if kind != "silver" else 0
        stone_cost = round(rng.uniform(600, 3200), 0) if kind == "diamond" else 0
        if dname == "Diamond Pendant MS": stone_cost = 450
        silver_price = round(rng.uniform(55, 420), 0) if kind == "silver" else 0
        sup = sups[0] if (len(sups) == 1 or rng.random() < 0.6) else sups[1]
        if coll == "Temple Heritage": sup = "SUP04"
        for s in sizes:
            pid += 1
            wt = w
            if s and s.endswith("in"): wt = round(w * int(s[:2]) / 20, 1)
            if s in ("2.4", "2.6", "2.8"): wt = round(w * float(s) / 2.6, 1)
            if s in ("5", "6", "7", "8", "9"): wt = round(w * (0.9 + 0.05 * (int(s) - 5)), 1)
            prod_rows.append(dict(
                sku=f"SKU{pid:04d}", design_name=dname, category=cat, metal_type=kind,
                karat={"gold": "22K", "coin": "24K", "diamond": "18K", "silver": "925 Silver"}[kind],
                purity=purity, size=s if s else "", net_weight_g=wt, making_charge_pct=vapct,
                stone_cost_cad=stone_cost, stone_retail_cad=round(stone_cost * 1.85, 0),
                silver_list_price_cad=silver_price, primary_supplier_id=sup, collection=coll,
                launch_date=max(launch, date(2022, 1, 1)),
                _planned_pop=ppop, _actual_pop=apop,
                _size_share=SIZE_ACTUAL.get(s, 1.0) if s else 1.0,
                _planned_size_share=(1 / len(sizes)) if s else 1.0))
products = pd.DataFrame(prod_rows)
P = products.set_index("sku").to_dict("index")
SKUS_BY_CAT = products.groupby("category").sku.apply(list).to_dict()

# ------------------------------------------------------------------ demand structure
SEGMENTS = ["Wedding", "Festival & Gifting", "Everyday", "Investment", "Corporate"]
SEG_BASE = {"Wedding": 0.75, "Festival & Gifting": 1.45, "Everyday": 2.3, "Investment": 0.55, "Corporate": 0.03}
SEG_CATMIX = {
 "Wedding": {"Necklace Sets": .32, "Gold Bangles": .24, "Mangalsutra": .16, "Gold Earrings": .11,
             "Gold Chains": .09, "Diamond Rings": .05, "Gold Rings": .03},
 "Festival & Gifting": {"Gold Chains": .17, "Gold Earrings": .2, "Gold Rings": .13, "Gold Coins": .13,
                        "Gold Bangles": .09, "Silver Jewellery": .16, "Diamond Earrings": .06, "Diamond Rings": .06},
 "Everyday": {"Gold Rings": .2, "Gold Earrings": .2, "Gold Chains": .17, "Silver Jewellery": .23,
              "Diamond Earrings": .1, "Diamond Rings": .1},
 "Investment": {"Gold Coins": .92, "Gold Chains": .08},
 "Corporate": {"Gold Coins": .55, "Silver Jewellery": .45},
}
SEG_LINES = {"Wedding": (2, 4), "Festival & Gifting": (1, 2), "Everyday": (1, 2), "Investment": (1, 1), "Corporate": (1, 1)}
WED_MONTH = {1: 1.45, 2: 1.35, 3: .9, 4: 1.1, 5: 1.2, 6: .85, 7: .6, 8: .65, 9: .8, 10: 1.0, 11: 1.45, 12: 1.5}
DIWALI = {2023: date(2023, 11, 12), 2024: date(2024, 11, 1), 2025: date(2025, 10, 20), 2026: date(2026, 11, 8)}
AKSHAYA = {2023: date(2023, 4, 22), 2024: date(2024, 5, 10), 2025: date(2025, 4, 30), 2026: date(2026, 4, 20)}

def mothers_day(y):
    d = date(y, 5, 1)
    first_sun = d + timedelta((6 - d.weekday()) % 7)
    return first_sun + timedelta(7)

def season(d):
    m = {s: 1.0 for s in SEGMENTS}
    m["Wedding"] = WED_MONTH[d.month]
    dw = DIWALI[d.year]; dh = dw - timedelta(2); ak = AKSHAYA[d.year]
    delta = (d - dw).days
    festive_flag = "No Event"
    if d == dh:
        m["Festival & Gifting"] *= 5; m["Investment"] *= 9; festive_flag = "Dhanteras"
    elif -12 <= delta <= 2:
        m["Festival & Gifting"] *= 2.4; m["Investment"] *= 2; festive_flag = "Diwali season"
    elif -30 <= delta < -12:
        m["Festival & Gifting"] *= 1.5; festive_flag = "Navratri/Dussehra"
    if -25 <= delta <= 0: m["Corporate"] *= 18
    else: m["Corporate"] *= 0.3
    da = (d - ak).days
    if da == 0: m["Investment"] *= 7; m["Festival & Gifting"] *= 2.5; festive_flag = "Akshaya Tritiya"
    elif -3 <= da <= 2: m["Investment"] *= 2; m["Festival & Gifting"] *= 1.5; festive_flag = "Akshaya Tritiya"
    if date(d.year, 2, 7) <= d <= date(d.year, 2, 14): m["Everyday"] *= 2.0; festive_flag = (festive_flag if festive_flag != "No Event" else None) or "Valentine's"
    md = mothers_day(d.year)
    if md - timedelta(6) <= d <= md: m["Everyday"] *= 1.7; festive_flag = (festive_flag if festive_flag != "No Event" else None) or "Mother's Day"
    if date(d.year, 12, 8) <= d <= date(d.year, 12, 24): m["Everyday"] *= 2.1; m["Festival & Gifting"] *= 1.3; festive_flag = (festive_flag if festive_flag != "No Event" else None) or "Christmas"
    if date(d.year, 8, 10) <= d <= date(d.year, 8, 25): m["Festival & Gifting"] *= 1.25
    return m, festive_flag

DOW = [0.75, 0.8, 0.85, 0.95, 1.15, 1.45, 1.25]  # Mon..Sun

# ------------------------------------------------------------------ inventory planning
def exp_cat_lines_per_day(store):
    out = defaultdict(float)
    for s in SEGMENTS:
        lo, hi = SEG_LINES[s]; nl = (lo + hi) / 2
        for c, w in SEG_CATMIX[s].items():
            out[c] += SEG_BASE[s] * nl * w * SF[store] * 1.05
    return out
EXP = {s: exp_cat_lines_per_day(s) for s in STORE_IDS}
CAT_POP_SUM = {c: sum(P[k]["_planned_pop"] * P[k]["_planned_size_share"] for k in ks) for c, ks in SKUS_BY_CAT.items()}

def prior_daily(sku, store):
    p = P[sku]
    return EXP[store][p["category"]] * p["_planned_pop"] * p["_planned_size_share"] / CAT_POP_SUM[p["category"]]

on_hand = defaultdict(int); avg_cost = defaultdict(float); on_order = defaultdict(int)
last_sale = {}; last_receipt = {}
sales_hist = defaultdict(list)  # (sku,store) -> list of sale dates
inbound = defaultdict(list)      # date -> list of po dicts
po_rows = []; po_seq = 0

def unit_cost(sku, d, sup_id=None):
    p = P[sku]; s = SUP[sup_id or p["primary_supplier_id"]]
    if p["metal_type"] == "silver":
        return round(p["silver_list_price_cad"] * 0.42, 2)
    rate = GOLD[d]
    metal = p["net_weight_g"] * p["purity"] * rate * (1 + s["gold_wastage_pct"])
    return round(metal + s["labour_cad_per_g"] * p["net_weight_g"] + p["stone_cost_cad"], 2)

def place_po(sku, store, d, qty, reason):
    global po_seq
    p = P[sku]; sup = p["primary_supplier_id"]; s = SUP[sup]
    po_seq += 1
    L = s["standard_lead_time_days"]
    late = rng.random() > s["on_time_rate_target"]
    actual = max(2, L + int(rng.integers(-4, 1))) + (int(rng.integers(3, max(5, int(L * 0.5)))) if late else 0)
    exp_d = d + timedelta(L); rec_d = d + timedelta(actual)
    po = dict(po_id=f"PO{po_seq:06d}", supplier_id=sup, store_id=store, sku=sku, order_date=d,
              expected_date=exp_d, received_date=rec_d, qty_ordered=qty, reason=reason)
    po_rows.append(po)
    inbound[rec_d].append(po)
    on_order[(sku, store)] += qty

def reorder_levels(sku, store, d):
    L = SUP[P[sku]["primary_supplier_id"]]["standard_lead_time_days"]
    hist = [x for x in sales_hist[(sku, store)] if (d - x).days <= 120]
    trailing = len(hist) / 120
    age = (d - P[sku]["launch_date"]).days
    w = 0.3 if age > 150 else 0.0   # planners slow to react to actual demand
    dd = (1 - w) * prior_daily(sku, store) * store_ramp(store, d) + w * trailing
    cover = L + 7
    rop = dd * cover + 1.0 * np.sqrt(dd * cover)
    S = rop + dd * 75                      # ~2.5 months of cycle stock
    mn = 2 if P[sku]["category"] not in ("Necklace Sets", "Diamond Rings") else 1   # display minimum
    return max(mn, int(np.ceil(rop))), max(mn + 1, int(np.ceil(S)))

def initial_stock(d, stores_to_stock, skus):
    for st in stores_to_stock:
        for sku in skus:
            rop, S = reorder_levels(sku, st, d)
            qty = S + (3 if P[sku]["collection"] == "Temple Heritage" else 0)
            on_hand[(sku, st)] += qty
            avg_cost[(sku, st)] = unit_cost(sku, max(START, d - timedelta(30)))
            last_receipt[(sku, st)] = d

# ------------------------------------------------------------------ simulation
sales_rows, ret_rows, miss_rows = [], [], []
returns_due = defaultdict(list)
cust_rows = []; cust_by_store = defaultdict(list); cid = 0
inv_seq = 0; line_seq = 0
snap_rows = []
CITY = {"ST01": ["Brampton"] * 6 + ["Caledon", "Mississauga", "Vaughan"],
        "ST02": ["Mississauga"] * 6 + ["Oakville", "Milton", "Brampton"],
        "ST03": ["Toronto"] * 6 + ["Scarborough", "Markham", "Ajax"]}

def get_customer(store, d, seg):
    global cid
    if seg != "Corporate" and cust_by_store[store] and rng.random() < 0.42:
        return cust_by_store[store][int(rng.integers(len(cust_by_store[store])))]
    cid += 1
    c = f"C{cid:06d}"
    cust_rows.append(dict(customer_id=c, home_store_id=store, city=rng.choice(CITY[store]),
                          first_purchase_date=d, primary_segment=seg,
                          gold_savings_plan_member=bool(rng.random() < (0.18 if seg != "Corporate" else 0)),
                          customer_type="Business" if seg == "Corporate" else "Individual"))
    if seg != "Corporate": cust_by_store[store].append(c)
    return c

def available(sku, d):
    return P[sku]["launch_date"] <= d

def pick_sku(cat, d):
    ks = [k for k in SKUS_BY_CAT[cat] if available(k, d)]
    w = np.array([P[k]["_actual_pop"] * P[k]["_size_share"] for k in ks]); w /= w.sum()
    return ks[rng.choice(len(ks), p=w)]

stocked_launch = set()
initial_stock(START, ["ST01", "ST02"], [k for k in P if available(k, START)])
for k in P:
    if available(k, START): stocked_launch.add(k)

def price_line(sku, d, seg, flag, qty):
    p = P[sku]
    if p["metal_type"] == "silver":
        lp = p["silver_list_price_cad"] * (GOLD[d] / G0) ** 0.25
        disc = 0.15 if flag in ("Christmas", "Diwali season") else (0.10 if seg == "Corporate" else 0)
        gross = round(lp * qty, 2)
        return 0.0, 0.0, 0.0, gross, round(gross * disc, 2)
    metal = p["net_weight_g"] * p["purity"] * GOLD[d] * qty
    making = metal * p["making_charge_pct"]
    if flag in ("Dhanteras", "Akshaya Tritiya"): dpct = rng.uniform(0.30, 0.50)
    elif flag in ("Diwali season", "Navratri/Dussehra"): dpct = rng.uniform(0.15, 0.30)
    elif seg == "Wedding": dpct = rng.uniform(0.10, 0.20)
    else: dpct = rng.choice([0, 0, 0.05, 0.10])
    if p["collection"] == "Temple Heritage" and d >= date(2026, 3, 1): dpct = max(dpct, 0.45)  # markdown
    stone = p["stone_retail_cad"] * qty
    return round(metal, 2), round(making, 2), round(stone, 2), 0.0, round(making * dpct, 2)

for d in DATES:
    # store opening -> initial stock
    if d == OPEN["ST03"]:
        initial_stock(d, ["ST03"], [k for k in P if available(k, d)])
    # new collection launch -> launch buy for open stores
    for k in P:
        if k not in stocked_launch and P[k]["launch_date"] == d:
            pass
    launching = [k for k in P if k not in stocked_launch and P[k]["launch_date"] <= d]
    if launching:
        initial_stock(d, [s for s in STORE_IDS if d >= OPEN[s]], launching)
        stocked_launch.update(launching)
    # receive POs
    for po in inbound.pop(d, []):
        key = (po["sku"], po["store_id"])
        uc = unit_cost(po["sku"], d)
        po["unit_cost_cad"] = uc; po["gold_rate_24k_on_receipt"] = GOLD[d]
        tot = on_hand[key] * avg_cost[key] + po["qty_ordered"] * uc
        on_hand[key] += po["qty_ordered"]; on_order[key] -= po["qty_ordered"]
        avg_cost[key] = tot / on_hand[key]; last_receipt[key] = d
    # process returns (restock)
    for r in returns_due.pop(d, []):
        key = (r["sku"], r["store_id"])
        tot = on_hand[key] * avg_cost[key] + r["qty"] * r["_unit_cost"]
        on_hand[key] += r["qty"]; avg_cost[key] = tot / on_hand[key]
    mult, flag = season(d)
    yrs = (d - START).days / 365
    gold_eff = (GOLD[d] / G0) ** -0.32
    for st in STORE_IDS:
        ramp = store_ramp(st, d)
        if ramp == 0: continue
        for seg in SEGMENTS:
            lam = SEG_BASE[seg] * mult[seg] * SF[st] * ramp * DOW[d.weekday()] * (1.05 ** yrs)
            if seg != "Corporate": lam *= gold_eff if seg != "Everyday" else gold_eff ** 0.6
            n = rng.poisson(lam)
            for _ in range(n):
                inv_seq += 1; inv = f"INV{inv_seq:07d}"
                cust = get_customer(st, d, seg) if (seg in ("Wedding", "Corporate") or rng.random() > 0.10) else ""
                lo, hi = SEG_LINES[seg]; nl = int(rng.integers(lo, hi + 1))
                cats = list(SEG_CATMIX[seg]); w = np.array([SEG_CATMIX[seg][c] for c in cats])
                chosen = rng.choice(cats, size=min(nl, len(cats)), replace=False, p=w / w.sum())
                pay = rng.choice(["Credit Card", "Debit", "Cash", "Old Gold Exchange", "E-Transfer"],
                                 p=[.38, .24, .10, .16, .12])
                for cat in chosen:
                    qty = int(rng.integers(5, 26)) if seg == "Corporate" else (int(rng.integers(1, 3)) if seg == "Investment" else 1)
                    sku = pick_sku(cat, d)
                    key = (sku, st)
                    if on_hand[key] < qty:
                        alts = [k for k in SKUS_BY_CAT[cat] if available(k, d) and on_hand[(k, st)] >= qty
                                and P[k]["size"] == P[sku]["size"] and k != sku]
                        miss_rows.append(dict(request_date=d, store_id=st, sku_requested=sku, category=cat,
                                              qty=qty, substituted=bool(alts and rng.random() < 0.4)))
                        if miss_rows[-1]["substituted"]:
                            sku = alts[int(rng.integers(len(alts)))]; key = (sku, st)
                            miss_rows[-1]["substitute_sku"] = sku
                        else:
                            continue
                    metal, making, stone, silver, disc = price_line(sku, d, seg, flag, qty)
                    net = round(metal + making + stone + silver - disc, 2)
                    cogs = round(avg_cost[key] * qty, 2)
                    on_hand[key] -= qty; last_sale[key] = d; sales_hist[key].extend([d] * qty)
                    line_seq += 1
                    row = dict(line_id=f"L{line_seq:07d}", invoice_id=inv, sale_date=d, store_id=st,
                               customer_id=cust, customer_segment=seg, sku=sku, qty=qty,
                               gold_rate_24k_cad=GOLD[d], net_weight_g=round(P[sku]["net_weight_g"] * qty, 2),
                               metal_value_cad=metal, making_charge_cad=making, stone_value_cad=stone,
                               silver_item_value_cad=silver, discount_cad=disc, net_sales_cad=net,
                               hst_cad=round(net * 0.13, 2), cogs_cad=cogs, payment_method=pay,
                               promo_event=flag)
                    sales_rows.append(row)
                    # returns / exchanges
                    pr = {"Wedding": .01, "Festival & Gifting": .045, "Everyday": .03, "Investment": .004, "Corporate": 0}[seg]
                    if P[sku]["metal_type"] == "silver": pr *= 1.6
                    if rng.random() < pr:
                        rd = d + timedelta(int(rng.integers(2, 31)))
                        if rd <= END:
                            rr = dict(return_id=f"R{len(ret_rows)+1:06d}", line_id=row["line_id"], invoice_id=inv,
                                      return_date=rd, store_id=st, sku=sku, qty=qty,
                                      return_type=rng.choice(["Exchange", "Refund", "Store Credit"], p=[.55, .25, .20]),
                                      reason=rng.choice(["Size issue", "Gift - changed mind", "Design preference",
                                                         "Minor defect", "Duplicate gift"], p=[.3, .25, .25, .1, .1]),
                                      refund_amount_cad=net, cogs_reversed_cad=cogs, _unit_cost=cogs / qty)
                            ret_rows.append(rr); returns_due[rd].append(rr)
    # weekly reorder review (Mondays) + launch-free days
    if d.weekday() == 0:
        for st in STORE_IDS:
            if store_ramp(st, d) == 0: continue
            for sku in P:
                if not available(sku, d): continue
                if P[sku]["collection"] == "Temple Heritage" and d >= date(2026, 1, 15): continue  # stopped reordering
                key = (sku, st)
                rop, S = reorder_levels(sku, st, d)
                pos = on_hand[key] + on_order[key]
                if pos <= rop:
                    place_po(sku, st, d, max(1, S - pos), "Replenishment")
    # month-end snapshot
    if (d + timedelta(1)).day == 1:
        for st in STORE_IDS:
            if d < OPEN[st]: continue
            for sku in P:
                if not available(sku, d): continue
                key = (sku, st)
                snap_rows.append(dict(snapshot_date=d, store_id=st, sku=sku, on_hand_qty=on_hand[key],
                                      on_order_qty=on_order[key], avg_unit_cost_cad=round(avg_cost[key], 2),
                                      inventory_cost_value_cad=round(avg_cost[key] * on_hand[key], 2),
                                      gold_rate_24k_cad=GOLD[d],
                                      days_since_last_sale=(d - last_sale[key]).days if key in last_sale else None,
                                      days_since_last_receipt=(d - last_receipt[key]).days if key in last_receipt else None))

# ------------------------------------------------------------------ assemble
sales = pd.DataFrame(sales_rows)
returns = pd.DataFrame(ret_rows).drop(columns=["_unit_cost"])
missed = pd.DataFrame(miss_rows)
snaps = pd.DataFrame(snap_rows)
customers = pd.DataFrame(cust_rows)
pos = pd.DataFrame(po_rows)
pos["status"] = np.where(pd.to_datetime(pos.received_date) <= pd.Timestamp(END), "Received", "Open")
pos.loc[pos.status == "Open", ["received_date"]] = None
for c in ["unit_cost_cad", "gold_rate_24k_on_receipt"]:
    if c not in pos: pos[c] = np.nan
pos["total_cost_cad"] = (pos.unit_cost_cad * pos.qty_ordered).round(2)
pos["gold_wastage_pct"] = pos.supplier_id.map(lambda s: SUP[s]["gold_wastage_pct"])
pos = pos[["po_id", "supplier_id", "store_id", "sku", "order_date", "expected_date", "received_date", "status",
           "qty_ordered", "gold_wastage_pct", "gold_rate_24k_on_receipt", "unit_cost_cad", "total_cost_cad", "reason"]]

# ------------------------------------------------------------------ opex
sales["month"] = pd.to_datetime(sales.sale_date).dt.to_period("M")
ms = sales.groupby(["store_id", "month"]).agg(net=("net_sales_cad", "sum")).reset_index()
card = sales[sales.payment_method.isin(["Credit Card", "Debit"])].copy()
card["fee"] = np.where(card.payment_method == "Credit Card", 0.019, 0.006) * (card.net_sales_cad + card.hst_cad)
cardfee = card.groupby(["store_id", "month"]).fee.sum()
opex_rows = []
HC = dict(zip(stores.store_id, stores.headcount)); RENT = dict(zip(stores.store_id, stores.monthly_rent_cad))
for r in ms.itertuples():
    m = r.month; y = m.year
    infl = 1.03 ** (y - 2023)
    festive = m.month in (9, 10, 11) or (m.month == 4)
    items = {
        "Rent & Occupancy": RENT[r.store_id] * infl,
        "Salaries & Wages": HC[r.store_id] * 4300 * infl * (1.12 if m.month in (10, 11, 12) else 1),
        "Sales Commission": r.net * 0.006,
        "Marketing & Advertising": (2500 + (9000 if festive else 0)) * SF[r.store_id] * rng.uniform(.85, 1.15),
        "Card Processing Fees": cardfee.get((r.store_id, m), 0),
        "Insurance & Security": 3200 * SF[r.store_id] * infl,
        "Utilities": 1400 * SF[r.store_id] * rng.uniform(.85, 1.2),
        "Repairs & Maintenance": (2200 if m.month in (1, 4, 7, 10) else 450) * rng.uniform(.8, 1.2),
        "Other G&A": 1300 * SF[r.store_id] * rng.uniform(.9, 1.1),
    }
    for k, v in items.items():
        opex_rows.append(dict(month=str(m), store_id=r.store_id, expense_category=k, amount_cad=round(v, 2)))
opex = pd.DataFrame(opex_rows)

# ------------------------------------------------------------------ FY2026 budget (prepared Dec 2025)
BUDGET_GOLD = 165.0
s25 = sales[pd.to_datetime(sales.sale_date).dt.year == 2025].merge(products[["sku", "category", "metal_type"]], on="sku")
s25["m"] = pd.to_datetime(s25.sale_date).dt.month
g = s25.groupby(["store_id", "category", "m"]).agg(units=("qty", "sum"), weight=("net_weight_g", "sum"),
                                                     net=("net_sales_cad", "sum"), cogs=("cogs_cad", "sum"),
                                                     rate=("gold_rate_24k_cad", "mean")).reset_index()
bud = []
growth = {"ST01": 1.05, "ST02": 1.06, "ST03": 1.15}
for r in g.itertuples():
    units = r.units * growth[r.store_id]
    kind = CATS[r.category][0]
    price_adj = (BUDGET_GOLD / r.rate) if kind in ("gold", "coin") else ((BUDGET_GOLD / r.rate) * 0.5 + 0.5 if kind == "diamond" else 1.03)
    net_b = r.net / r.units * units * price_adj
    gm_pct = 1 - r.cogs / r.net if r.net else 0
    bud.append(dict(month=f"2026-{r.m:02d}", store_id=r.store_id, category=r.category,
                    budget_units=round(units, 1), budget_gold_rate_24k_cad=BUDGET_GOLD,
                    budget_net_sales_cad=round(net_b, 2), budget_gross_margin_pct=round(gm_pct, 4),
                    budget_gross_profit_cad=round(net_b * gm_pct, 2)))
budget = pd.DataFrame(bud)
ob = opex[opex.month.str.startswith("2025")].copy()
ob["month"] = ob.month.str.replace("2025", "2026")
ob["budget_amount_cad"] = (ob.amount_cad * 1.04).round(2)
opex_budget = ob.drop(columns="amount_cad")

# ------------------------------------------------------------------ inject data-quality issues (raw exports)
sales_raw = sales.drop(columns="month").copy()
sales_raw["sale_date"] = pd.to_datetime(sales_raw.sale_date).dt.strftime("%Y-%m-%d")
dup = sales_raw.sample(frac=0.004, random_state=1)                       # duplicate lines (double export)
sales_raw = pd.concat([sales_raw, dup]).sort_values(["sale_date", "line_id"]).reset_index(drop=True)
idx = sales_raw.sample(frac=0.003, random_state=2).index                 # messy store codes
sales_raw.loc[idx, "store_id"] = sales_raw.loc[idx, "store_id"].map(lambda s: rng.choice([s.lower(), s + " ", f" {s}"]))
idx = sales_raw.sample(frac=0.002, random_state=3).index                 # date in DD/MM/YYYY
sales_raw.loc[idx, "sale_date"] = pd.to_datetime(sales_raw.loc[idx, "sale_date"]).dt.strftime("%d/%m/%Y")
idx = sales_raw.sample(n=6, random_state=4).index                        # missing net_sales (recompute)
sales_raw.loc[idx, "net_sales_cad"] = np.nan
idx = sales_raw[sales_raw.customer_segment == "Everyday"].sample(n=25, random_state=5).index
sales_raw.loc[idx, "customer_segment"] = "everyday"                       # inconsistent case

prod_out = products[[c for c in products.columns if not c.startswith("_")]].copy()
idx = prod_out.sample(n=5, random_state=6).index
prod_out.loc[idx, "category"] = prod_out.loc[idx, "category"] + " "     # trailing spaces
prod_out.loc[prod_out.sample(n=2, random_state=7).index, "net_weight_g"] = np.nan

# ------------------------------------------------------------------ write
def w(df, name): df.to_csv(os.path.join(OUT, name), index=False)
w(gold_df, "gold_rates_daily.csv")
w(stores.drop(columns="size_factor"), "dim_stores.csv")
w(suppliers.drop(columns="on_time_rate_target"), "dim_suppliers.csv")
w(prod_out, "dim_products.csv")
w(customers, "dim_customers.csv")
w(sales_raw, "fact_sales_raw.csv")
w(returns, "fact_returns.csv")
w(pos, "fact_purchase_orders.csv")
w(snaps, "fact_inventory_month_end.csv")
w(missed, "fact_missed_requests.csv")
w(opex, "fact_opex_monthly.csv")
w(budget, "budget_fy2026_sales.csv")
w(opex_budget, "budget_fy2026_opex.csv")
print("rows:", {"sales": len(sales_raw), "returns": len(returns), "POs": len(pos), "snapshots": len(snaps),
                "missed": len(missed), "customers": len(customers), "products": len(products)})
