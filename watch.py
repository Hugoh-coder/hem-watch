# /// script
# requires-python = ">=3.10"
# dependencies = ["curl_cffi"]
# ///
"""hem-watch: aggregated apartment hunt for Kungsholmen/Vasastan/Södermalm.

Criteria: bostadsrätt, <= 6 000 000 kr, >= 40 kvm, balkong (hard filter).
Sources: Hemnet (incl. kommande) + Booli (which itself crawls most mäklare
sites, so broker-only listings arrive through it). Deduped by address+kvm.
Diskmaskin/tvättmaskin detected from listing descriptions -> badges (✓/?),
never a hard filter (many listings have them without saying so).

  uv run watch.py          # scrape, print NEW listings, write matches.json

State next to this file: seen_ids.json (id -> first-seen date, drives NY tag),
desc_cache.json (listing id -> {dm, tm} so descriptions are fetched once).
Both sites are Cloudflare-protected; curl_cffi's Chrome impersonation passes.
"""
import datetime
import json
import pathlib
import re

from curl_cffi import requests

HERE = pathlib.Path(__file__).parent
PRICE_MAX = 6_000_000
KVM_MIN = 40
HEMNET_LOCATIONS = ["898472", "925968", "925970"]  # Södermalm, Kungsholmen, Vasastan
BOOLI_AREAS = "115341,115353,115349"               # same three, Booli ids
MAX_PAGES = 8
DM = re.compile(r"diskmaskin", re.I)
TM = re.compile(r"tvättmaskin|tvättpelare|egen tvätt", re.I)
# sekelskifte charm signals, matched in descriptions -> chips on the site
CHARM = [("stuckatur", re.compile(r"stuckatur|stuck i tak", re.I)),
         ("spegeldörrar", re.compile(r"spegeldörr", re.I)),
         ("takhöjd", re.compile(r"takhöjd|högt i tak", re.I)),
         ("sekelskifte", re.compile(r"sekelskift", re.I))]
CACHE_V = 2  # bump to refetch details (old entries lack byggår/plan/charm)

session = requests.Session(impersonate="chrome")


def get(url):
    r = session.get(url, timeout=40)
    r.raise_for_status()
    return r.text


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]


def resolve(ap, node):
    """Follow one level of apollo __ref indirection."""
    if isinstance(node, dict) and "__ref" in node:
        return ap.get(node["__ref"], {})
    return node or {}


def num(text):
    """First integer in a formatted Swedish string ('5 095 000 kr' -> 5095000)."""
    if not text:
        return None
    t = re.sub(r"[   ]", "", str(text))
    m = re.search(r"\d+", t)
    return int(m.group()) if m else None


def norm_addr(addr):
    # Hemnet decorates addresses ("Rålambsvägen 29, 4 Tr") — key on the part
    # before the comma, up to and including the street number/letter.
    a = (addr or "").split(",")[0].lower().replace("é", "e")
    a = re.sub(r"[^a-z0-9åäö ]", "", a).strip()
    m = re.match(r"(.*?\d+\s*[a-z]?)\b", a)
    if m:
        a = m.group(1)
    return a.replace(" ", "")


# ---------------------------------------------------------------- Hemnet

def hemnet():
    items = []
    for page in range(1, MAX_PAGES + 1):
        url = ("https://www.hemnet.se/bostader?item_types%5B%5D=bostadsratt"
               f"&price_max={PRICE_MAX}&living_area_min={KVM_MIN}&balcony=1"
               + "".join(f"&location_ids%5B%5D={i}" for i in HEMNET_LOCATIONS)
               + f"&page={page}")
        pp = next_data(get(url))
        ap = pp["__APOLLO_STATE__"]
        refs, total = [], 0
        for k, v in ap["ROOT_QUERY"].items():
            if k.startswith(("searchForSaleListings", "searchUpcomingListings")) and isinstance(v, dict):
                total = max(total, v.get("total") or 0)
                for field in v.values():
                    if isinstance(field, list) and field and isinstance(field[0], dict) and "__ref" in field[0]:
                        refs += field
        page_cards = 0
        for ref in refs:
            c = resolve(ap, ref)
            if c.get("__typename") != "ListingCard":
                continue
            kvm = num(c.get("livingAndSupplementalAreas"))
            price = num(c.get("askingPrice"))
            if kvm is None or kvm < KVM_MIN or (price and price > PRICE_MAX):
                continue
            page_cards += 1
            items.append({
                "id": f"hemnet:{c['id']}",
                "src": "Hemnet",
                "url": f"https://www.hemnet.se/bostad/{c['slug']}",
                "address": c.get("streetAddress") or "",
                "area": (c.get("locationDescription") or "").split(",")[0].strip(),
                "price": price,
                "fee": num(c.get("fee")),
                "kvm": kvm,
                "rooms": c.get("rooms") and num(c["rooms"]),
                "floor": c.get("floor") or "",
                "sqm_price": num(c.get("squareMeterPrice")),
                "published": (c.get("publishedAt") or "")[:10],
                "upcoming": bool(c.get("upcoming")),
                "teaser": c.get("description") or "",
            })
        if page * 50 >= total or page_cards == 0:
            break
    return items


# ---------------------------------------------------------------- Booli

def booli_datapoints(ap, listing):
    out = {}
    for k, v in listing.items():
        if k.startswith("displayAttributes") and isinstance(v, dict):
            for dp in v.get("dataPoints", []):
                t = ((dp.get("value") or {}).get("plainText")) or ""
                if "m²" in t and "kr" not in t:
                    out["kvm"] = num(t)
                elif "rum" in t:
                    out["rooms"] = num(t)
                elif "kr/mån" in t:
                    out["fee"] = num(t)
                elif t.startswith("vån"):
                    out["floor"] = t
    return out


def booli():
    items, pages = [], 1
    page = 1
    while page <= min(pages, MAX_PAGES):
        url = (f"https://www.booli.se/sok/till-salu?areaIds={BOOLI_AREAS}"
               f"&maxListPrice={PRICE_MAX}&minLivingArea={KVM_MIN}"
               f"&objectType=L%C3%A4genhet&page={page}")
        pp = next_data(get(url))
        ap = pp["__APOLLO_STATE__"]
        for k, v in ap["ROOT_QUERY"].items():
            if k.startswith("searchForSale(") and "forceOnly" not in k and isinstance(v, dict):
                pages = v.get("pages") or 1
                for ref in v.get("result", []):
                    L = resolve(ap, ref)
                    if L.get("__typename") != "Listing":
                        continue
                    amen = [json.loads(r["__ref"].split(":", 1)[1])["key"]
                            for r in L.get("amenities") or [] if "__ref" in r]
                    if "balcony" not in amen:
                        continue  # balcony is a hard requirement
                    dp = booli_datapoints(ap, L)
                    kvm = dp.get("kvm")
                    lp = L.get("listPrice")
                    price = lp.get("raw") if isinstance(lp, dict) else num(lp)
                    if kvm is None or kvm < KVM_MIN or (price and price > PRICE_MAX):
                        continue
                    sqm = L.get("listSqmPrice")
                    items.append({
                        "id": f"booli:{L['booliId']}",
                        "src": "Booli",
                        "url": "https://www.booli.se" + L["url"],
                        "address": L.get("streetAddress") or "",
                        "area": L.get("descriptiveAreaName") or "",
                        "price": price,
                        "fee": dp.get("fee"),
                        "kvm": kvm,
                        "rooms": dp.get("rooms"),
                        "floor": dp.get("floor", ""),
                        "sqm_price": sqm.get("raw") if isinstance(sqm, dict) else num(sqm),
                        "published": (L.get("published") or "")[:10],
                        "upcoming": bool(L.get("upcomingSale")),
                        "teaser": "",
                    })
        page += 1
    return items


# ---------------------------------- details (badges, byggår, planritning)

def hemnet_details(plain_id, html, out):
    """Description, byggår and floorplan all sit on the '<...>PropertyListing:{id}'
    apollo entity (the page also embeds similar-listings teasers, so only that
    entity is used)."""
    ap = next_data(html).get("__APOLLO_STATE__", {})
    for k, v in ap.items():
        if k.endswith(f"PropertyListing:{plain_id}") and isinstance(v, dict):
            out["byggar"] = num(v.get("legacyConstructionYear"))
            for ik, iv in v.items():
                if ik.startswith("images(") and isinstance(iv, dict):
                    for img in iv.get("images") or []:
                        if "FLOOR_PLAN" in (img.get("labels") or []):
                            url = next((u for uk, u in img.items() if uk.startswith("url")), None)
                            out["plan"] = out["plan"] or url
            return v.get("description") or ""
    return ""


def booli_details(plain_id, html, out):
    """Byggår + floorplan from the Booli page apollo; the description only lives
    on the broker's own page (listingUrl), so fetch that for the text."""
    ap = next_data(html).get("__APOLLO_STATE__", {})
    L = ap.get(f"Listing:{plain_id}") or next(
        (v for v in ap.values() if isinstance(v, dict) and v.get("constructionYear")), {})
    out["byggar"] = L.get("constructionYear")
    for k, v in ap.items():
        if k.startswith("Image:") and isinstance(v, dict) and v.get("primaryLabel") == "floorplan":
            out["plan"] = f"https://bcdn.se/images/cache/{v['id']}_1440x0.jpg"
            break
    m = re.search(r'"listingUrl"\s*:\s*"(https?://[^"]+)"', html)
    if not m:
        return ""
    out["broker_url"] = m.group(1)
    # ponytail: verify=False — some mäklare sites ship broken cert chains; read-only scrape
    return session.get(m.group(1), timeout=40, verify=False).text


def listing_details(item, cache):
    """dm/tm badges, byggår, planritning url, charm signals — one cached fetch."""
    hit = cache.get(item["id"])
    if hit and hit.get("v") == CACHE_V:
        return hit
    out = {"v": CACHE_V, "byggar": None, "plan": None}
    try:
        html = get(item["url"])
        src, plain_id = item["id"].split(":")
        text = (hemnet_details if src == "hemnet" else booli_details)(plain_id, html, out)
    except Exception as e:
        print(f"  ! detail fetch failed {item['url']}: {e}")
        return {"dm": None, "tm": None, "byggar": None, "plan": None, "charm": []}  # not cached -> retried next run
    text = text or item.get("teaser", "")
    out["dm"] = bool(DM.search(text)) or None
    out["tm"] = bool(TM.search(text)) or None
    out["charm"] = [name for name, rx in CHARM if rx.search(text)]
    cache[item["id"]] = out
    return out


# ---------------------------------------------------------------- main

def dedupe(items):
    """Same address + kvm (±1, sources round differently) = one apartment.
    Hemnet wins as primary; the other source becomes an 'also' link."""
    kept = []
    for it in sorted(items, key=lambda x: x["src"] != "Hemnet"):  # Hemnet first
        addr = norm_addr(it["address"])
        # exact kvm always merges; ±1 only across sources (rounding differs) —
        # same-source ±1 can be two real units in one building
        twin = next((k for k in kept if addr and norm_addr(k["address"]) == addr
                     and (k["kvm"] == it["kvm"]
                          or (k["src"] != it["src"] and abs(k["kvm"] - it["kvm"]) <= 1))), None)
        if twin:
            twin.setdefault("also", []).append({"src": it["src"], "url": it["url"]})
            for f in ("price", "fee", "rooms", "sqm_price"):  # fill gaps from dupe
                if twin.get(f) is None:
                    twin[f] = it.get(f)
        else:
            kept.append(it)
    return kept


def main():
    h = hemnet()
    b = booli()
    print(f"hemnet: {len(h)}  booli: {len(b)}")
    items = dedupe(h + b)

    cache_p = HERE / "desc_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for it in items:
        d = dict(listing_details(it, cache))
        d.pop("v", None)
        it.update(d)
        it.pop("teaser", None)
    cache_p.write_text(json.dumps(cache))

    seen_p = HERE / "seen_ids.json"
    seen = json.loads(seen_p.read_text()) if seen_p.exists() else {}
    today = datetime.date.today().isoformat()
    for it in items:
        first = seen.get(it["id"], today)
        seen[it["id"]] = first
        it["first_seen"] = first
        it["new"] = first == today
    seen_p.write_text(json.dumps(seen, indent=0))

    items.sort(key=lambda x: (x["first_seen"], x["published"]), reverse=True)
    (HERE / "matches.json").write_text(json.dumps(
        {"updated": today, "items": items}, ensure_ascii=False, indent=1))
    news = [it for it in items if it["new"]]
    print(f"total after dedupe: {len(items)}  ({len(news)} new)")
    for it in news:
        pris = f"{it['price']:,} kr".replace(",", " ") if it["price"] else "kommande"
        print(f"  NY {it['address']} ({it['area']}) {it['kvm']} kvm — {pris} [{it['src']}]")


if __name__ == "__main__":
    main()
