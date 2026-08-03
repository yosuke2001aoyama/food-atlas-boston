#!/usr/bin/env python3
"""Build durable Vercel JSON snapshots from the Streamlit app's source of truth."""

from __future__ import annotations

import ast
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "app.py"
OVERPASS_SOURCE = Path("/tmp/hometaste-overpass.json")
CHECKS_SOURCE = Path("/tmp/hometaste-reviews.csv")
DATA_DIR = ROOT / "data"


def app_constants() -> dict[str, object]:
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    wanted = {"COUNTRY_FLAGS", "COUNTRY_CUISINES", "FALLBACK_RESTAURANTS", "CURATED_MAJOR_RESTAURANTS"}
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in wanted:
            values[target.id] = ast.literal_eval(node.value)
    missing = wanted - values.keys()
    if missing:
        raise RuntimeError(f"Missing app constants: {sorted(missing)}")
    return values


def normalize_cuisines(value: str) -> set[str]:
    return {
        cuisine.strip().lower().replace(" ", "_")
        for cuisine in value.replace(",", ";").split(";")
        if cuisine.strip()
    }


def name_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def area_for(latitude: float, longitude: float) -> str:
    centers = {
        "Back Bay / South End": (42.3475, -71.0800),
        "Boston Downtown": (42.3570, -71.0585),
        "Brighton / Allston": (42.3500, -71.1360),
        "Brookline": (42.3417, -71.1212),
        "Cambridge": (42.3736, -71.1097),
        "Chinatown": (42.3502, -71.0620),
        "East Boston": (42.3751, -71.0390),
        "Fenway / Kenmore": (42.3458, -71.0988),
        "Jamaica Plain / Roxbury": (42.3126, -71.1140),
        "North End": (42.3655, -71.0542),
        "Somerville / Medford": (42.3950, -71.1050),
    }
    return min(centers, key=lambda name: (
        (latitude - centers[name][0]) ** 2
        + ((longitude - centers[name][1]) * 0.75) ** 2
    ))


def restaurant_record(name: str, country: str, cuisine: str, latitude: float, longitude: float, *, source: str) -> dict[str, object]:
    return {
        "name": name.strip(),
        "country": country,
        "cuisine": cuisine,
        "latitude": round(float(latitude), 7),
        "longitude": round(float(longitude), 7),
        "area": area_for(float(latitude), float(longitude)),
        "source": source,
    }


def build_restaurants(constants: dict[str, object]) -> list[dict[str, object]]:
    if not OVERPASS_SOURCE.exists():
        raise RuntimeError(f"Missing {OVERPASS_SOURCE}; fetch the original Overpass query first")
    raw = json.loads(OVERPASS_SOURCE.read_text(encoding="utf-8"))
    country_cuisines: dict[str, set[str]] = constants["COUNTRY_CUISINES"]  # type: ignore[assignment]
    curated: list[dict[str, object]] = constants["CURATED_MAJOR_RESTAURANTS"]  # type: ignore[assignment]
    canonical = {
        "ittoku": "Izakaya Ittoku",
        "izakayaittoku": "Izakaya Ittoku",
        "sugidama": "Sugidama Soba & Izakaya",
        "sugidamasobaizakaya": "Sugidama Soba & Izakaya",
        "cafemami": "Cafe Mami",
        "yumegaarukara": "Yume Ga Arukara",
        "yumewokatare": "Yume Wo Katare",
    }
    curated_by_key = {name_key(str(item["name"])): item for item in curated}
    restaurants: dict[str, dict[str, object]] = {}

    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        cuisine_text = tags.get("cuisine", "")
        latitude = element.get("lat") or element.get("center", {}).get("lat")
        longitude = element.get("lon") or element.get("center", {}).get("lon")
        if not name or not cuisine_text or latitude is None or longitude is None:
            continue
        cuisines = normalize_cuisines(cuisine_text)
        country = next((label for label, tokens in country_cuisines.items() if cuisines & tokens), None)
        if not country:
            continue
        key = name_key(name)
        canonical_name = canonical.get(key, name)
        canonical_key = name_key(canonical_name)
        if canonical_key in restaurants:
            continue
        curated_match = curated_by_key.get(canonical_key)
        if curated_match:
            restaurants[canonical_key] = restaurant_record(
                str(curated_match["name"]),
                str(curated_match["country"]),
                str(curated_match["cuisine"]),
                float(curated_match["latitude"]),
                float(curated_match["longitude"]),
                source="curated + OpenStreetMap",
            )
        else:
            restaurants[canonical_key] = restaurant_record(
                canonical_name,
                country,
                ", ".join(sorted(cuisines)),
                latitude,
                longitude,
                source="OpenStreetMap",
            )

    for item in curated:
        key = name_key(str(item["name"]))
        if key not in restaurants:
            restaurants[key] = restaurant_record(
                str(item["name"]),
                str(item["country"]),
                str(item["cuisine"]),
                float(item["latitude"]),
                float(item["longitude"]),
                source="curated",
            )

    return sorted(restaurants.values(), key=lambda item: str(item["name"]).casefold())


def normalized_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def first_value(row: dict[str, str], candidates: list[str]) -> str:
    normalized = {normalized_key(key): value for key, value in row.items()}
    return next((normalized.get(normalized_key(candidate), "") for candidate in candidates if normalized.get(normalized_key(candidate))), "")


def parse_checks() -> list[dict[str, object]]:
    if not CHECKS_SOURCE.exists():
        return []
    checks: list[dict[str, object]] = []
    with CHECKS_SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            restaurant = first_value(row, ["restaurant", "レストラン", "店", "店舗"])
            rating = first_value(row, ["rating", "score", "your rating", "評価", "採点"])
            if not restaurant or not rating:
                continue
            try:
                numeric_rating = float(rating)
            except ValueError:
                continue
            note = first_value(row, ["note", "notes", "comment", "explanation", "備考", "コメント"])
            relationship = "Legacy HomeTaste check"
            marker = "Relationship to cuisine:"
            for line in note.splitlines():
                if line.startswith(marker):
                    relationship = line.removeprefix(marker).strip() or relationship
            checks.append({
                "timestamp": first_value(row, ["timestamp", "time", "日時", "タイムスタンプ"]),
                "country": first_value(row, ["country", "home country", "国", "出身国"]),
                "restaurant": restaurant,
                "rating": numeric_rating,
                "note": note.split("\n\nRelationship to cuisine:", 1)[0].strip(),
                "relationship": relationship,
            })
    return checks


def main() -> None:
    constants = app_constants()
    restaurants = build_restaurants(constants)
    checks = parse_checks()
    countries = []
    labels = {
        "Argentina": "Argentinian",
        "Australia": "Australian",
        "Belgium": "Belgian",
        "Brazil": "Brazilian",
        "Cambodia": "Cambodian",
        "Canada": "Canadian",
        "China / Taiwan / Hong Kong": "Chinese / Taiwanese / Hong Kong",
        "Colombia": "Colombian",
        "Cuba": "Cuban",
        "Dominican Republic": "Dominican",
        "Egypt": "Egyptian",
        "Ethiopia": "Ethiopian",
        "Finland": "Finnish",
        "France": "French",
        "Germany": "German",
        "Georgia": "Georgian",
        "Ghana": "Ghanaian",
        "Greece": "Greek",
        "India": "Indian",
        "Indonesia": "Indonesian",
        "Iran": "Persian / Iranian",
        "Ireland": "Irish",
        "Israel": "Israeli",
        "Italy": "Italian",
        "Jamaica": "Jamaican",
        "Japan": "Japanese",
        "Korea": "Korean",
        "Lebanon": "Lebanese",
        "Malaysia": "Malaysian",
        "Mexico": "Mexican",
        "Morocco": "Moroccan",
        "Netherlands": "Dutch",
        "Nepal": "Nepalese",
        "Nigeria": "Nigerian",
        "Norway": "Norwegian",
        "Pakistan": "Pakistani",
        "Peru": "Peruvian",
        "Philippines": "Filipino",
        "Poland": "Polish",
        "Portugal": "Portuguese",
        "Russia": "Russian",
        "Singapore": "Singaporean",
        "Spain": "Spanish",
        "Sri Lanka": "Sri Lankan",
        "Sweden": "Swedish",
        "Switzerland": "Swiss",
        "Thailand": "Thai",
        "Turkey": "Turkish",
        "Ukraine": "Ukrainian",
        "United Kingdom": "British",
        "United States": "American",
        "Vietnam": "Vietnamese",
    }
    for country in constants["COUNTRY_CUISINES"]:  # type: ignore[union-attr]
        label = labels.get(country)
        if not label:
            label = country
        countries.append({
            "country": country,
            "label": label,
            "flag": constants["COUNTRY_FLAGS"].get(country, ""),  # type: ignore[union-attr]
        })

    DATA_DIR.mkdir(exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    (DATA_DIR / "restaurants.json").write_text(json.dumps({
        "generatedAt": generated_at,
        "source": "OpenStreetMap + HomeTaste curated records",
        "count": len(restaurants),
        "restaurants": restaurants,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA_DIR / "checks.json").write_text(json.dumps({
        "generatedAt": generated_at,
        "source": "HomeTaste published Google Sheet",
        "count": len(checks),
        "checks": checks,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA_DIR / "cuisines.json").write_text(json.dumps(countries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"restaurants": len(restaurants), "checks": len(checks), "cuisines": len(countries)}))


if __name__ == "__main__":
    main()
