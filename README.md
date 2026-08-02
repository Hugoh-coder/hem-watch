# hem-watch

Aggregated apartment hunt: **Kungsholmen, Vasastan, Södermalm** · max **6 mkr** ·
minst **40 kvm** · **balkong** (hard filter) · diskmaskin/tvättmaskin as badges.

**Live site:** https://hugoh-coder.github.io/hem-watch/

## How it works

- `watch.py` — scrapes **Hemnet** (incl. kommande) and **Booli** via their embedded
  `__NEXT_DATA__` JSON (curl_cffi Chrome impersonation gets past Cloudflare).
  Booli itself crawls most mäklare sites, so broker-only listings arrive that way.
  Listings are deduped by street address + kvm (±1 across sources); Hemnet wins as
  primary, the twin becomes an extra link on the card.
- Diskmaskin/tvättmaskin are read from the full listing description (Hemnet page,
  or the broker's own page via Booli's `listingUrl`). `✓` = mentioned, `?` = not
  mentioned — which is not a no. Cached in `desc_cache.json` so each listing is
  fetched once.
- `build_site.py` — renders `docs/index.html` (GitHub Pages) with district/badge
  filters and NY tags driven by `seen_ids.json`.
- `.github/workflows/refresh.yml` — daily 06:30 Swedish time, commits the refreshed
  page + state back.

## Run locally

```bash
uv run watch.py
python3 build_site.py
open docs/index.html
```

## Tuning

Criteria live at the top of `watch.py` (`PRICE_MAX`, `KVM_MIN`, area id lists —
Hemnet ids via `hemnet.se/locations/show?q=...`, Booli ids in the 1153xx range).
