#!/usr/bin/env python3
"""Build docs/index.html (GitHub Pages) from matches.json.

  uv run watch.py     # -> matches.json
  python3 build_site.py
"""
import datetime
import html as html_mod
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
DOCS = HERE / "docs"
UPDATED = datetime.date.today().strftime("%-d %B %Y")

DISTRICTS = [
    ("Kungsholmen", r"kungsholm|essinge|fredhäll|marieberg|stadshagen|kristineberg|lindhagen|hornsberg"),
    ("Vasastan", r"vasastan|hagastaden|birkastan|röda bergen|vasastaden|norrmalm|tegnérlunden"),
    ("Södermalm", r"södermalm|reimersholme|hornstull|högalid|katarina|sofia|maria|södra station|tanto|zinken"),
]


def district(item):
    hay = f"{item.get('area', '')} {item.get('address', '')}".lower()
    for name, pat in DISTRICTS:
        if re.search(pat, hay):
            return name
    return ""


def js(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    data = json.loads((HERE / "matches.json").read_text())
    items = data["items"]
    rows = []
    for it in items:
        rows.append("    {{ addr:{addr}, area:{area}, dist:{dist}, price:{price}, fee:{fee}, "
                    "kvm:{kvm}, rooms:{rooms}, floor:{floor}, sqm:{sqm}, dm:{dm}, tm:{tm}, "
                    "up:{up}, isnew:{isnew}, seen:{seen}, src:{src}, url:{url}, burl:{burl}, "
                    "yr:{yr}, plan:{plan}, charm:{charm}, also:{also} }},".format(
            addr=js(it["address"]), area=js(it["area"]), dist=js(district(it)),
            price=it["price"] or "null", fee=it["fee"] or "null", kvm=it["kvm"],
            rooms=it["rooms"] or "null", floor=js(it.get("floor") or ""),
            sqm=it["sqm_price"] or "null",
            dm="true" if it.get("dm") else "null", tm="true" if it.get("tm") else "null",
            up="true" if it.get("upcoming") else "false",
            isnew="true" if it.get("new") else "false", seen=js(it["first_seen"]),
            src=js(it["src"]), url=js(it["url"]), burl=js(it.get("broker_url") or ""),
            yr=it.get("byggar") or "null", plan=js(it.get("plan") or ""),
            charm=js(it.get("charm") or []),
            also=js(it.get("also") or [])))
    page = (PAGE_TPL
            .replace("__COUNT__", str(len(items)))
            .replace("__UPDATED__", UPDATED)
            .replace("__ROWS__", "\n".join(rows)))
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page)
    print(f"wrote docs/index.html: {len(items)} apartments")


STYLE = r"""<style>
  :root {
    --bg:#f5f3ee; --surface:#fffefb; --ink:#23272b; --ink-soft:#5b6167; --line:#e0dcd2;
    --accent:#0e9b8a; --accent-ink:#fff; --chip:#e7f3f1; --chip-ink:#0c6d61;
    --warn:#b45309; --warn-bg:#fdf0e0;
    --shadow:0 1px 2px rgba(30,30,30,.05), 0 6px 16px rgba(30,30,30,.06);
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171a; --surface:#1d2125; --ink:#eef0f2; --ink-soft:#a2abb2; --line:#30363c;
      --accent:#3fd0bd; --accent-ink:#0c1214; --chip:#17342f; --chip-ink:#6fe0d0;
      --warn:#f0a75c; --warn-bg:#33270f;
      --shadow:0 1px 2px rgba(0,0,0,.3), 0 6px 18px rgba(0,0,0,.35); }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; line-height:1.5;
    -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1040px; margin:0 auto; padding:0 18px; }
  header { position:sticky; top:0; z-index:10;
    background:color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter:blur(8px);
    border-bottom:1px solid var(--line); }
  .head-inner { padding:18px 18px 14px; max-width:1040px; margin:0 auto; }
  h1 { margin:0; font-size:1.5rem; font-weight:800; letter-spacing:-.02em; }
  .sub { margin:3px 0 0; color:var(--ink-soft); font-size:.9rem; }
  .sub b { color:var(--ink); font-variant-numeric:tabular-nums; }
  .controls { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:13px; }
  .filters { display:flex; flex-wrap:wrap; gap:6px; }
  button.f, button.sort { font:inherit; font-size:.85rem; font-weight:600; padding:6px 13px;
    border-radius:999px; border:1px solid var(--line); background:var(--surface);
    color:var(--ink-soft); cursor:pointer; }
  button.f:hover, button.sort:hover { border-color:var(--accent); color:var(--ink); }
  button.f.on { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
  .right-btns { margin-left:auto; display:flex; gap:6px; flex-wrap:wrap; }
  main { padding:20px 0 60px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
  .card { display:flex; flex-direction:column; gap:8px; background:var(--surface);
    border:1px solid var(--line); border-radius:14px; padding:15px 16px 16px;
    color:inherit; box-shadow:var(--shadow); }
  .card-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
  .tags { display:flex; gap:5px; }
  .tag { font-size:.68rem; font-weight:700; padding:2px 8px; border-radius:6px; letter-spacing:.02em; }
  .tag.ny { background:var(--accent); color:var(--accent-ink); }
  .tag.upc { background:var(--warn-bg); color:var(--warn); }
  .dist { font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.07em;
    color:var(--chip-ink); background:var(--chip); padding:3px 9px; border-radius:6px; }
  .price { font-size:1.25rem; font-weight:800; font-variant-numeric:tabular-nums; }
  .price.upc { color:var(--warn); font-size:1.05rem; }
  .addr { font-size:1rem; font-weight:650; line-height:1.3; }
  .area { color:var(--ink-soft); font-size:.82rem; }
  .meta { display:flex; flex-wrap:wrap; gap:4px 12px; color:var(--ink-soft); font-size:.82rem; }
  .meta b { color:var(--ink); font-weight:600; }
  .badges { display:flex; gap:6px; flex-wrap:wrap; }
  .bdg { font-size:.74rem; padding:3px 9px; border-radius:999px; border:1px solid var(--line); color:var(--ink-soft); }
  .bdg.yes { background:var(--chip); color:var(--chip-ink); border-color:transparent; font-weight:600; }
  .bdg.charm { background:var(--warn-bg); color:var(--warn); border-color:transparent; font-weight:600; }
  .plan { display:block; }
  .plan img { width:100%; height:170px; object-fit:contain; background:#fff;
    border:1px solid var(--line); border-radius:9px; }
  .links { display:flex; gap:12px; margin-top:auto; padding-top:6px; border-top:1px dashed var(--line); }
  .links a { font-size:.85rem; font-weight:700; color:var(--accent); text-decoration:none; }
  .links a:hover { text-decoration:underline; }
  .empty { text-align:center; color:var(--ink-soft); padding:50px 20px; }
  footer { border-top:1px solid var(--line); padding:22px 0 40px; color:var(--ink-soft); font-size:.8rem; }
  footer p { margin:0 0 7px; }
</style>"""

PAGE_TPL = ("<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Hemjakten · Kungsholmen · Vasastan · Södermalm</title>\n") + STYLE + r"""
<header><div class="head-inner">
  <h1>Hemjakten 🏡</h1>
  <p class="sub"><b id="count">__COUNT__</b> lägenheter · max 6 mkr · minst 40 kvm · balkong ·
    Hemnet + Booli (inkl. mäklarnas egna & kommande)</p>
  <div class="controls">
    <div class="filters" id="distFilters"></div>
    <div class="filters">
      <button class="f" id="fDm">✓ Diskmaskin</button>
      <button class="f" id="fTm">✓ Tvättmaskin</button>
      <button class="f" id="fUp">Dölj kommande</button>
      <button class="f" id="fSk">✨ Sekelskifte</button>
    </div>
    <div class="right-btns"><button class="sort" id="sortBtn">Nyast först</button></div>
  </div>
</div></header>
<main><div class="wrap">
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" hidden>Inget matchar filtren just nu.</div>
</div></main>
<footer><div class="wrap">
  <p>Uppdaterad <b>__UPDATED__</b>, automatiskt varje morgon. Booli bevakar de flesta mäklarsajter,
    så mäklar-exklusiva objekt fångas den vägen.</p>
  <p>✓-märken för diskmaskin/tvättmaskin läses ur annonstexten — en lägenhet kan ha dem utan att
    texten nämner det, så okänd betyder inte nej. Balkong är hårt krav i sökningen.</p>
  <p>✨ Sekelskifte = byggår före 1930 (sekelskifte + 20-talsklassicism, hög takhöjd) eller
    stuckatur/spegeldörrar/takhöjd nämnt i annonsen. Funkis och senare (1930–) har oftast ~2,5 m i tak.</p>
</div></footer>
<script>
  const flats = [
__ROWS__
  ];
  let dist = "Alla", needDm = false, needTm = false, hideUp = false, needSk = false, sortNew = true;
  // sekelskifte = byggår före 1930 (funkis och senare har lägre takhöjd) eller
  // charm-signal i annonstexten (stuckatur/spegeldörrar/takhöjd/sekelskifte)
  const isSekel = f => (f.yr && f.yr <= 1929) || f.charm.length > 0;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
  const safeUrl = u => /^https?:\/\//i.test(u) ? u : "#";
  const kr = n => n.toLocaleString("sv-SE") + " kr";

  const distEl = document.getElementById("distFilters");
  ["Alla", "Kungsholmen", "Vasastan", "Södermalm"].forEach(d => {
    const b = document.createElement("button");
    b.className = "f" + (d === "Alla" ? " on" : "");
    b.textContent = d;
    b.onclick = () => { dist = d;
      distEl.querySelectorAll("button").forEach(x => x.classList.toggle("on", x.textContent === d));
      render(); };
    distEl.appendChild(b);
  });
  const toggle = (id, set) => { const b = document.getElementById(id);
    b.onclick = () => { b.classList.toggle("on"); set(b.classList.contains("on")); render(); }; };
  toggle("fDm", v => needDm = v);
  toggle("fTm", v => needTm = v);
  toggle("fUp", v => hideUp = v);
  toggle("fSk", v => needSk = v);
  const sortBtn = document.getElementById("sortBtn");
  sortBtn.onclick = () => { sortNew = !sortNew;
    sortBtn.textContent = sortNew ? "Nyast först" : "Pris: lägst först ↑"; render(); };

  function render() {
    const grid = document.getElementById("grid");
    let list = flats.filter(f =>
      (dist === "Alla" || f.dist === dist) &&
      (!needDm || f.dm) && (!needTm || f.tm) && (!hideUp || !f.up) && (!needSk || isSekel(f)));
    list.sort(sortNew
      ? (a, b) => (b.seen + (b.isnew ? "1" : "0")).localeCompare(a.seen + (a.isnew ? "1" : "0"))
      : (a, b) => (a.price ?? 1e9) - (b.price ?? 1e9));
    grid.innerHTML = list.map(f => `
      <div class="card">
        <div class="card-top">
          <span class="dist">${esc(f.dist || f.area)}</span>
          <span class="tags">
            ${f.isnew ? '<span class="tag ny">NY</span>' : ""}
            ${f.up ? '<span class="tag upc">KOMMANDE</span>' : ""}
          </span>
        </div>
        <div class="price${f.up && !f.price ? " upc" : ""}">${f.price ? esc(kr(f.price)) : "Pris ej satt"}</div>
        <div class="addr">${esc(f.addr)}</div>
        <div class="area">${esc(f.area)}</div>
        ${f.plan ? `<a class="plan" href="${safeUrl(f.plan)}" target="_blank" rel="noopener">
          <img src="${safeUrl(f.plan)}" loading="lazy" referrerpolicy="no-referrer" alt="Planritning"></a>` : ""}
        <div class="meta">
          <span><b>${f.kvm}</b> kvm</span>
          ${f.rooms ? `<span><b>${f.rooms}</b> rum</span>` : ""}
          ${f.floor ? `<span>${esc(f.floor)}</span>` : ""}
          ${f.yr ? `<span>byggd <b>${f.yr}</b></span>` : ""}
          ${f.fee ? `<span>${esc(f.fee.toLocaleString("sv-SE"))} kr/mån</span>` : ""}
          ${f.sqm ? `<span>${esc(f.sqm.toLocaleString("sv-SE"))} kr/m²</span>` : ""}
        </div>
        <div class="badges">
          <span class="bdg${f.dm ? " yes" : ""}">${f.dm ? "✓" : "?"} diskmaskin</span>
          <span class="bdg${f.tm ? " yes" : ""}">${f.tm ? "✓" : "?"} tvättmaskin</span>
          ${f.charm.map(c => `<span class="bdg charm">✨ ${esc(c)}</span>`).join("")}
        </div>
        <div class="links">
          <a href="${safeUrl(f.url)}" target="_blank" rel="noopener">${esc(f.src)} ↗</a>
          ${f.also.map(a => `<a href="${safeUrl(a.url)}" target="_blank" rel="noopener">${esc(a.src)} ↗</a>`).join("")}
          ${f.burl ? `<a href="${safeUrl(f.burl)}" target="_blank" rel="noopener">Mäklaren ↗</a>` : ""}
        </div>
      </div>`).join("");
    document.getElementById("count").textContent = list.length;
    document.getElementById("empty").hidden = list.length > 0;
  }
  render();
</script>"""


if __name__ == "__main__":
    main()
