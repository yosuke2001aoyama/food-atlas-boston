#!/usr/bin/env python3
"""Build crawlable cuisine landing pages, sitemap.xml, and robots.txt."""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://hometaste-boston.vercel.app"
LAST_MODIFIED = "2026-08-04"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1400&q=86"
IMAGE_BY_SLUG = {
    "japanese": "https://images.unsplash.com/photo-1516684808441-d7ca9141e63c?auto=format&fit=crop&w=1400&q=86",
    "chinese-taiwanese-hong-kong": "https://images.unsplash.com/photo-1525755662778-989d0524087e?auto=format&fit=crop&w=1400&q=86",
    "italian": "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=1400&q=86",
    "mexican": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=1400&q=86",
    "indian": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=1400&q=86",
    "korean": "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?auto=format&fit=crop&w=1400&q=86",
    "vietnamese": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?auto=format&fit=crop&w=1400&q=86",
}


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", normalized.lower()))


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def json_ld(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def head(title: str, description: str, canonical: str, image: str, schema: dict) -> str:
    return f"""  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#ffffff" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1" />
  <link rel="canonical" href="{esc(canonical)}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="stylesheet" href="/seo.css" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="HomeTaste Boston" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{esc(canonical)}" />
  <meta property="og:image" content="{esc(image)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(description)}" />
  <meta name="twitter:image" content="{esc(image)}" />
  <script type="application/ld+json">{json_ld(schema)}</script>"""


def page_shell(page_head: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
{page_head}
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header class="site-header">
    <a class="wordmark" href="/" aria-label="HomeTaste Boston home"><span class="brand-mark" aria-hidden="true">H</span><span>HomeTaste <em>Boston</em></span></a>
    <nav aria-label="Primary navigation"><a href="/">Restaurant map</a><a href="/cuisines">All cuisines</a><a class="nav-cta" href="/#voices">HomeTaste voices</a></nav>
  </header>
{body}
  <footer><div><strong>HomeTaste Boston</strong><p>Find the places that taste like home — to someone.</p></div><nav aria-label="Footer navigation"><a href="/">Restaurant map</a><a href="/cuisines">Browse cuisines</a><a href="https://www.openstreetmap.org/copyright" rel="noreferrer">Map data</a></nav></footer>
</body>
</html>
"""


def cuisine_index(cuisines: list[dict], grouped: dict[str, list[dict]]) -> str:
    represented = [item for item in cuisines if grouped.get(item["country"])]
    total = sum(len(grouped[item["country"]]) for item in represented)
    title = "Boston Restaurants by Cuisine | HomeTaste Boston"
    description = f"Browse {total:,} Boston-area restaurants by cuisine, spanning {len(cuisines)} food cultures, then open the live HomeTaste map for neighborhood filters and lived-experience context."
    canonical = f"{BASE_URL}/cuisines"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": "Boston restaurants by cuisine",
                "url": canonical,
                "description": description,
                "isPartOf": {"@type": "WebSite", "name": "HomeTaste Boston", "url": f"{BASE_URL}/"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": "Cuisines", "item": canonical},
                ],
            },
            {
                "@type": "ItemList",
                "numberOfItems": len(represented),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": position,
                        "name": f'{item["label"]} restaurants in Boston',
                        "url": f'{BASE_URL}/cuisines/{slugify(item["label"])}',
                    }
                    for position, item in enumerate(represented, 1)
                ],
            },
        ],
    }
    cards = "".join(
        f"""<a class="cuisine-list-card" href="/cuisines/{slugify(item['label'])}"><span class="flag" aria-hidden="true">{esc(item['flag'])}</span><span><strong>{esc(item['label'])}</strong><small>{len(grouped[item['country']]):,} places</small></span><span class="arrow" aria-hidden="true">→</span></a>"""
        for item in represented
    )
    body = f"""  <main id="content">
    <section class="index-hero"><p class="eyebrow">THE COMPLETE BOSTON ATLAS</p><h1>Boston restaurants,<br />organized by cuisine.</h1><p>Explore every represented food culture in the current HomeTaste dataset. Each guide preserves the same restaurant listings as the live map and adds a search-friendly way to browse them.</p><a class="button" href="/#explore">Open the interactive map</a></section>
    <section class="content-section" aria-labelledby="cuisine-list-title"><div class="section-heading"><div><p class="eyebrow">BROWSE FOOD CULTURES</p><h2 id="cuisine-list-title">{len(represented)} cuisines with listings</h2></div><p>{total:,} restaurants are currently mapped. HomeTaste checks add lived-experience context; they do not certify one correct version of a cuisine.</p></div><div class="cuisine-list">{cards}</div></section>
  </main>"""
    return page_shell(head(title, description, canonical, DEFAULT_IMAGE, schema), body)


def cuisine_page(cuisine: dict, restaurants: list[dict], checked_names: set[str], represented: list[dict]) -> str:
    country = cuisine["country"]
    label = cuisine["label"]
    slug = slugify(label)
    canonical = f"{BASE_URL}/cuisines/{slug}"
    count = len(restaurants)
    areas = Counter(item.get("area") or "Boston area" for item in restaurants)
    top_areas = [area for area, _ in areas.most_common(3)]
    area_phrase = ", ".join(top_areas)
    title = f"{label} Restaurants in Boston ({count:,} Places) | HomeTaste"
    description = f"Browse {count:,} {label} restaurants around Boston, including {area_phrase}. Compare neighborhoods and open every listing on the live HomeTaste map."
    ordered = sorted(restaurants, key=lambda item: (normalize_name(item["name"]) not in checked_names, item["name"].casefold()))
    featured = ordered[:24]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": f"{label} restaurants in Boston",
                "url": canonical,
                "description": description,
                "isPartOf": {"@type": "WebSite", "name": "HomeTaste Boston", "url": f"{BASE_URL}/"},
                "about": {"@type": "Thing", "name": f"{label} cuisine"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": "Cuisines", "item": f"{BASE_URL}/cuisines"},
                    {"@type": "ListItem", "position": 3, "name": label, "item": canonical},
                ],
            },
            {
                "@type": "ItemList",
                "name": f"{label} restaurants in the HomeTaste Boston dataset",
                "numberOfItems": count,
                "itemListElement": [
                    {"@type": "ListItem", "position": position, "name": item["name"]}
                    for position, item in enumerate(featured, 1)
                ],
            },
        ],
    }
    map_url = f"/?cuisine={quote(country, safe='')}#explore"
    cards = "".join(
        f"""<article class="restaurant-list-card"><div><p>{esc(item.get('area') or 'Boston area')}</p><h3>{esc(item['name'])}</h3><span>{esc(str(item.get('cuisine') or label).replace('_', ' '))}</span></div><a href="{map_url}" aria-label="Find {esc(item['name'])} on the restaurant map">View on map <span aria-hidden="true">→</span></a></article>"""
        for item in featured
    )
    more_note = f"Showing 24 of {count:,} places." if count > 24 else f"Showing all {count:,} place{'s' if count != 1 else ''}."
    siblings = [item for item in represented if item["country"] != country]
    start = next((index for index, item in enumerate(represented) if item["country"] == country), 0)
    related = (siblings[start % len(siblings):] + siblings[:start % len(siblings)])[:6] if siblings else []
    related_links = "".join(f'<a href="/cuisines/{slugify(item["label"])}">{esc(item["flag"])} {esc(item["label"])}</a>' for item in related)
    body = f"""  <main id="content">
    <section class="cuisine-hero" style="--hero-image:url('{esc(IMAGE_BY_SLUG.get(slug, DEFAULT_IMAGE))}')"><div><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/cuisines">Cuisines</a><span>/</span><span>{esc(label)}</span></nav><p class="eyebrow">{esc(cuisine['flag'])} {esc(label.upper())} FOOD IN BOSTON</p><h1>{esc(label)} restaurants<br />across Boston.</h1><p>Browse {count:,} places from the complete HomeTaste dataset, with listings concentrated around {esc(area_phrase)}.</p><a class="button" href="{map_url}">Explore all {count:,} on the map</a></div></section>
    <section class="content-section"><div class="section-heading"><div><p class="eyebrow">RESTAURANT DIRECTORY</p><h2>{esc(label)} places to explore</h2></div><p>{more_note} Listings with a published HomeTaste check appear first, followed alphabetically. Restaurant data comes from OpenStreetMap and HomeTaste.</p></div><div class="restaurant-list">{cards}</div><div class="map-cta"><div><p class="eyebrow">NEIGHBORHOOD SEARCH</p><h2>See every place on the live map.</h2><p>Filter by area, search by restaurant or dish, and open HomeTaste voices without losing the complete dataset.</p></div><a class="button" href="{map_url}">Open {esc(label)} map</a></div></section>
    <section class="context-section"><div><p class="eyebrow">HOW HOMETASTE WORKS</p><h2>Context from lived experience, open to every diner.</h2></div><p>Anyone can use this guide. People who grew up with, learned at home, or lived with {esc(label)} food can add concrete notes about what feels familiar. These voices add cultural context without declaring a single version of the cuisine the only correct one.</p></section>
    <section class="related-section"><div><h2>Explore more Boston cuisines</h2><a href="/cuisines">View all cuisines →</a></div><nav aria-label="Related cuisines">{related_links}</nav></section>
  </main>"""
    return page_shell(head(title, description, canonical, IMAGE_BY_SLUG.get(slug, DEFAULT_IMAGE), schema), body)


def main() -> None:
    restaurants = load_json("data/restaurants.json")["restaurants"]
    cuisines = load_json("data/cuisines.json")
    checks = load_json("data/checks.json")["checks"]
    checked_names = {normalize_name(item["restaurant"]) for item in checks}
    grouped: dict[str, list[dict]] = {}
    for restaurant in restaurants:
        grouped.setdefault(restaurant["country"], []).append(restaurant)
    represented = [item for item in cuisines if grouped.get(item["country"])]

    output = ROOT / "cuisines"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    (output / "index.html").write_text(cuisine_index(cuisines, grouped), encoding="utf-8")
    for cuisine in represented:
        directory = output / slugify(cuisine["label"])
        directory.mkdir()
        directory.joinpath("index.html").write_text(
            cuisine_page(cuisine, grouped[cuisine["country"]], checked_names, represented),
            encoding="utf-8",
        )

    urls = [f"{BASE_URL}/", f"{BASE_URL}/cuisines"] + [f"{BASE_URL}/cuisines/{slugify(item['label'])}" for item in represented]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{esc(url)}</loc><lastmod>{LAST_MODIFIED}</lastmod></url>\n" for url in urls
    ) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")
    print(json.dumps({"pages": len(represented) + 1, "sitemap_urls": len(urls), "restaurants": len(restaurants)}))


if __name__ == "__main__":
    main()
