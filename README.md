# hem-watch

Aggregated apartment hunt: **Kungsholmen, Vasastan, Södermalm** · max **6 mkr** ·
minst **40 kvm** · **balkong** (hard filter) · **ingen bottenvåning** (vån < 1 dropped) ·
diskmaskin/tvättmaskin as badges · planritning on every card that has one.

**Live site:** https://hugoh-coder.github.io/hem-watch/

Site filters: district · ✓ diskmaskin · ✓ tvättmaskin · dölj kommande ·
✨ sekelskifte (byggår ≤ 1929 or stuckatur/spegeldörrar/takhöjd/sekelskifte in the
listing text — since balkong is a base requirement, this toggle *is* "sekelskifte
och balkong") · max pris · max avgift · sort by newest/price.

## How it works

- `watch.py` — scrapes **Hemnet** (incl. kommande) and **Booli** via their embedded
  `__NEXT_DATA__` JSON (curl_cffi Chrome impersonation gets past Cloudflare).
  Booli itself crawls most mäklare sites, so broker-only listings arrive that way.
  Listings are deduped by street address + kvm (±1 across sources); Hemnet wins as
  primary, the twin becomes an extra link on the card.
- Each listing's detail page is fetched once (cached in `desc_cache.json`, versioned
  via `CACHE_V`) and yields: diskmaskin/tvättmaskin badges (`✓` = mentioned in the
  text, `?` = not mentioned — which is not a no), byggår (Hemnet
  `legacyConstructionYear` / Booli `constructionYear`), planritning image
  (Hemnet `FLOOR_PLAN`-labeled image / Booli floorplan image via bcdn.se), charm
  signals for the ✨ filter, and the broker's own page link (Booli `listingUrl` —
  also where descriptions for Booli-only listings come from).
- Bottenvåning: sources count ground floor as vån 0 ("vån 1" = 1 tr up), so
  anything below vån 1 is dropped at scrape time. Unknown floor is kept.
- `build_site.py` — renders `docs/index.html` (GitHub Pages) with district/badge
  filters and NY tags driven by `seen_ids.json`.
- Daily refresh runs **locally** via launchd (`com.hugo.hem-watch`, 06:30 — missed
  runs fire after the Mac wakes): `refresh.sh` scrapes, rebuilds and pushes; GitHub
  Pages just serves. GitHub Actions can't scrape here — Cloudflare 403s CI IPs.
  The repo really lives at `~/hem-watch` (launchd can't read `~/Documents` without
  extra permissions); `~/Documents/coding/hem-watch` is a symlink to it.

## Run locally

```bash
uv run watch.py
python3 build_site.py
open docs/index.html
```

## Tuning

Criteria live at the top of `watch.py` (`PRICE_MAX`, `KVM_MIN`, area id lists —
Hemnet ids via `hemnet.se/locations/show?q=...`, Booli ids in the 1153xx range).
