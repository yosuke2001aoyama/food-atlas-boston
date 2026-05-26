import csv
import html
import json
import os
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import folium
import streamlit as st
from streamlit_folium import st_folium


BOSTON_CENTER = [42.3601, -71.0589]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DATA_VERSION = "boston-restaurants-v8-curated-priority"
RATING_FORM_ANCHOR = "rate-restaurant"
FEEDBACK_FILE = "feedback.csv"
REVIEWS_FILE = "reviews.csv"

COUNTRY_FLAGS = {
    "Argentina": "🇦🇷",
    "Australia": "🇦🇺",
    "Belgium": "🇧🇪",
    "Brazil": "🇧🇷",
    "Cambodia": "🇰🇭",
    "Canada": "🇨🇦",
    "China / Taiwan / Hong Kong": "🇨🇳 🇹🇼 🇭🇰",
    "Colombia": "🇨🇴",
    "Cuba": "🇨🇺",
    "Dominican Republic": "🇩🇴",
    "Egypt": "🇪🇬",
    "Ethiopia": "🇪🇹",
    "Finland": "🇫🇮",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Georgia": "🇬🇪",
    "Ghana": "🇬🇭",
    "Greece": "🇬🇷",
    "India": "🇮🇳",
    "Indonesia": "🇮🇩",
    "Iran": "🇮🇷",
    "Ireland": "🇮🇪",
    "Israel": "🇮🇱",
    "Italy": "🇮🇹",
    "Jamaica": "🇯🇲",
    "Japan": "🇯🇵",
    "Korea": "🇰🇷",
    "Lebanon": "🇱🇧",
    "Malaysia": "🇲🇾",
    "Mexico": "🇲🇽",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "Nigeria": "🇳🇬",
    "Norway": "🇳🇴",
    "Nepal": "🇳🇵",
    "Pakistan": "🇵🇰",
    "Peru": "🇵🇪",
    "Philippines": "🇵🇭",
    "Poland": "🇵🇱",
    "Portugal": "🇵🇹",
    "Russia": "🇷🇺",
    "Singapore": "🇸🇬",
    "Spain": "🇪🇸",
    "Sri Lanka": "🇱🇰",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Thailand": "🇹🇭",
    "Turkey": "🇹🇷",
    "Ukraine": "🇺🇦",
    "United Kingdom": "🇬🇧",
    "United States": "🇺🇸",
    "Vietnam": "🇻🇳",
}

COUNTRY_CUISINES = {
    "Argentina": {"argentinian", "argentine", "empanada"},
    "Australia": {"australian"},
    "Belgium": {"belgian", "waffle"},
    "Brazil": {"brazilian", "churrasco"},
    "Cambodia": {"cambodian", "khmer"},
    "Canada": {"canadian", "poutine"},
    "China / Taiwan / Hong Kong": {
        "cantonese",
        "chinese",
        "dim_sum",
        "hong_kong",
        "hunan",
        "shanghainese",
        "sichuan",
        "szechuan",
        "taiwanese",
    },
    "Colombia": {"colombian"},
    "Cuba": {"cuban"},
    "Dominican Republic": {"dominican"},
    "Egypt": {"egyptian"},
    "Ethiopia": {"ethiopian"},
    "Finland": {"finnish"},
    "France": {"french, crepe", "french", "crepe"},
    "Germany": {"german", "biergarten"},
    "Georgia": {"georgian"},
    "Ghana": {"ghanaian"},
    "Greece": {"greek"},
    "India": {"indian"},
    "Indonesia": {"indonesian"},
    "Iran": {"persian", "iranian"},
    "Ireland": {"irish"},
    "Israel": {"israeli"},
    "Italy": {"italian", "pizza"},
    "Jamaica": {"jamaican"},
    "Japan": {"japanese", "sushi", "ramen", "udon", "yakitori", "izakaya"},
    "Korea": {"korean"},
    "Lebanon": {"lebanese"},
    "Malaysia": {"malaysian"},
    "Mexico": {"mexican", "taco", "tacos", "tex-mex"},
    "Morocco": {"moroccan"},
    "Netherlands": {"dutch"},
    "Nepal": {"nepalese"},
    "Nigeria": {"nigerian"},
    "Norway": {"norwegian"},
    "Pakistan": {"pakistani"},
    "Peru": {"peruvian"},
    "Philippines": {"filipino", "philippine"},
    "Poland": {"polish"},
    "Portugal": {"portuguese"},
    "Russia": {"russian"},
    "Singapore": {"singaporean"},
    "Spain": {"spanish", "tapas"},
    "Sri Lanka": {"sri_lankan", "srilankan"},
    "Sweden": {"swedish"},
    "Switzerland": {"swiss"},
    "Thailand": {"thai"},
    "Turkey": {"turkish", "mediterranean"},
    "Ukraine": {"ukrainian"},
    "United Kingdom": {"british", "english", "fish_and_chips"},
    "United States": {
        "american",
        "bagel",
        "barbecue",
        "bbq",
        "breakfast",
        "brunch",
        "burger",
        "chicken",
        "coffee_shop",
        "diner",
        "donut",
        "fish",
        "ice_cream",
        "juice",
        "regional",
        "sandwich",
        "seafood",
        "steak_house",
        "wings",
    },
    "Vietnam": {"vietnamese", "pho"},
}

FALLBACK_RESTAURANTS = [
    {"name": "Neptune Oyster", "country": "United States", "cuisine": "seafood", "latitude": 42.3631985, "longitude": -71.0559541},
    {"name": "Union Oyster House", "country": "United States", "cuisine": "seafood", "latitude": 42.36193, "longitude": -71.05697},
    {"name": "Regina Pizzeria", "country": "Italy", "cuisine": "pizza", "latitude": 42.36528, "longitude": -71.05608},
    {"name": "Giacomo's Ristorante", "country": "Italy", "cuisine": "italian", "latitude": 42.36398, "longitude": -71.05458},
    {"name": "O Ya", "country": "Japan", "cuisine": "japanese", "latitude": 42.35110, "longitude": -71.05685},
    {"name": "Yume Wo Katare", "country": "Japan", "cuisine": "ramen", "latitude": 42.3893688, "longitude": -71.1197175},
    {"name": "Yume Ga Arukara", "country": "Japan", "cuisine": "udon", "latitude": 42.3876285, "longitude": -71.1188077},
    {"name": "Toro", "country": "Spain", "cuisine": "spanish", "latitude": 42.33649, "longitude": -71.07569},
    {"name": "Myers+Chang", "country": "China / Taiwan / Hong Kong", "cuisine": "chinese", "latitude": 42.34302, "longitude": -71.06679},
    {"name": "Oleana", "country": "Turkey", "cuisine": "turkish", "latitude": 42.37056, "longitude": -71.09752},
    {"name": "India Quality Restaurant", "country": "India", "cuisine": "indian", "latitude": 42.34895, "longitude": -71.09699},
    {"name": "El Pelon Taqueria", "country": "Mexico", "cuisine": "mexican", "latitude": 42.34315, "longitude": -71.09925},
]

CURATED_MAJOR_RESTAURANTS = [
    {"name": "Izakaya Ittoku", "country": "Japan", "cuisine": "izakaya, japanese", "latitude": 42.38861, "longitude": -71.11918},
    {"name": "Sugidama Soba & Izakaya", "country": "Japan", "cuisine": "soba, izakaya, japanese", "latitude": 42.39672, "longitude": -71.12262},
    {"name": "Cafe Mami", "country": "Japan", "cuisine": "japanese, curry, donburi", "latitude": 42.38867, "longitude": -71.11915},
    {"name": "Yume Ga Arukara", "country": "Japan", "cuisine": "udon, japanese", "latitude": 42.3876285, "longitude": -71.1188077},
    {"name": "Yume Wo Katare", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.3893688, "longitude": -71.1197175},
    {"name": "Sapporo Ramen", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.36774, "longitude": -71.07672},
    {"name": "Tampopo", "country": "Japan", "cuisine": "japanese, donburi", "latitude": 42.38860, "longitude": -71.11918},
    {"name": "Cafe Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.38066, "longitude": -71.13848},
    {"name": "Cafe Sushi Shoten", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.36996, "longitude": -71.11194},
    {"name": "Maruichi Select", "country": "Japan", "cuisine": "japanese", "latitude": 42.34646, "longitude": -71.10841},
    {"name": "Hokkaido Ramen Santouka Harvard Square", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.37294, "longitude": -71.11899},
    {"name": "Hokkaido Ramen Santouka Back Bay", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.34857, "longitude": -71.08658},
    {"name": "Ganko Ittetsu Ramen", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.34295, "longitude": -71.12278},
    {"name": "Tsurumen Davis", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.39634, "longitude": -71.12286},
    {"name": "Hojoko", "country": "Japan", "cuisine": "japanese", "latitude": 42.34648, "longitude": -71.09588},
    {"name": "Douzo Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.34931, "longitude": -71.07493},
    {"name": "Basho Japanese Brasserie", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.34629, "longitude": -71.09868},
    {"name": "Fuji at Ink Block", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.34550, "longitude": -71.06367},
    {"name": "Genki Ya Boston", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35145, "longitude": -71.06483},
    {"name": "Yamato II", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35083, "longitude": -71.07724},
]

CURATED_PRIORITY = {
    restaurant["name"].strip().lower(): index
    for index, restaurant in enumerate(CURATED_MAJOR_RESTAURANTS)
}


st.set_page_config(page_title="Food Atlas Boston", layout="wide")

VIEW_OPTIONS = ["Explore", "Rate", "Reviews", "Feedback"]
VIEW_LABELS = {
    "Explore": "Explore",
    "Rate": "Rate",
    "Reviews": "Reviews",
    "Feedback": "Any issues?",
}
initial_view = st.query_params.get("view")
if isinstance(initial_view, list):
    initial_view = initial_view[0] if initial_view else None
if "active_view" not in st.session_state:
    st.session_state.active_view = initial_view if initial_view in VIEW_OPTIONS else "Explore"


def switch_view(view_name):
    st.session_state.active_view = view_name


st.markdown(
    """
    <style>
    :root {
        --accent: #a67c2d;
        --accent-dark: #6f4f1f;
        --accent-soft: #f4efe3;
        --ink: #17202d;
        --muted: #667085;
        --line: #ded6c7;
        --surface: #fbfaf6;
        --oxblood: #401f1f;
    }

    .stApp {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: linear-gradient(180deg, #f8fbfb 0%, #fbfaf6 38%, #ffffff 100%);
        color: var(--ink);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 5.8rem;
        padding-bottom: 3rem;
    }

    .stApp > header,
    [data-testid="stHeader"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid="stDecoration"],
    [data-testid="stDeployButton"],
    [data-testid="stBaseButton-header"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    h1 {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        letter-spacing: 0 !important;
        margin-bottom: 0.25rem !important;
    }

    h2, h3 {
        font-family: Georgia, "Times New Roman", serif;
        letter-spacing: 0 !important;
    }

    .brand-row {
        align-items: center;
        display: flex;
        gap: 0.65rem;
        margin-top: 0.15rem;
    }

    .brand-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1;
        white-space: nowrap;
    }

    .brand-mark {
        align-items: center;
        background: transparent;
        border: 1px solid rgba(166,124,45,0.45);
        border-radius: 999px;
        color: var(--accent-dark);
        display: inline-flex;
        height: 34px;
        justify-content: center;
        text-decoration: none;
        width: 34px;
    }

    .nav-bar-note {
        color: var(--muted);
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        margin: 0.35rem 0 0.5rem;
        text-transform: uppercase;
    }

    .hero {
        background:
            linear-gradient(90deg, rgba(18, 22, 28, 0.9), rgba(64, 31, 31, 0.42)),
            url("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1800&q=80");
        background-position: center;
        background-size: cover;
        border-radius: 8px;
        color: #ffffff;
        min-height: 430px;
        padding: 3.5rem 4rem;
        position: relative;
        overflow: hidden;
    }

    .hero-kicker {
        font-size: 0.9rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        margin-bottom: 0.8rem;
        text-transform: uppercase;
    }

    .hero-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 4rem;
        font-weight: 800;
        letter-spacing: 0 !important;
        line-height: 1.02;
        max-width: 720px;
    }

    .hero-subtitle {
        color: rgba(255, 255, 255, 0.88);
        font-size: 1.15rem;
        margin-top: 1rem;
        max-width: 620px;
    }

    .hero-search {
        align-items: center;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
        color: var(--ink);
        display: flex;
        gap: 1rem;
        margin-top: 2rem;
        max-width: 760px;
        padding: 0.85rem 0.9rem;
    }

    .hero-country-strip {
        background: rgba(251, 250, 246, 0.94);
        border: 1px solid rgba(222, 214, 199, 0.85);
        border-radius: 8px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.24);
        color: var(--ink);
        margin-top: 2rem;
        max-width: 850px;
        padding: 1rem;
    }

    .hero-country-title {
        color: var(--accent-dark);
        font-size: 0.82rem;
        font-weight: 900;
        letter-spacing: 0.06em;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
    }

    .hero-search-item {
        border-right: 1px solid var(--line);
        flex: 1;
        padding: 0 0.65rem;
    }

    .hero-search-item:last-child {
        border-right: 0;
    }

    .hero-search-label {
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .hero-search-value {
        font-size: 1.02rem;
        font-weight: 750;
        margin-top: 0.15rem;
    }

    .hero-search-button {
        align-items: center;
        background: linear-gradient(135deg, #0f7f8c, #1d4ed8);
        border-radius: 7px;
        color: #ffffff;
        display: flex;
        flex: 0 0 auto;
        font-weight: 900;
        gap: 0.55rem;
        min-height: 54px;
        padding: 0 1.2rem;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 1.25rem 0 2rem;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 8px 22px rgba(38, 38, 38, 0.06);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    .metric-value {
        color: var(--ink);
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.15;
        margin-top: 0.2rem;
    }

    .metric-icon {
        color: var(--accent);
        height: 30px;
        margin-top: 0.85rem;
        width: 30px;
    }

    .metric-icon svg {
        height: 30px;
        width: 30px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #17202d, #401f1f);
        border: 1px solid #17202d;
        border-radius: 6px;
        color: #ffffff;
        font-weight: 700;
        min-height: 2.7rem;
    }

    .stButton > button:hover {
        background: var(--oxblood);
        border-color: var(--oxblood);
        color: #ffffff;
    }

    div[data-testid="column"]:has(button[kind="tertiary"]) button,
    .stButton button[kind="tertiary"] {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: var(--muted) !important;
        font-weight: 750 !important;
        min-height: 2.3rem !important;
        padding: 0.2rem 0.35rem !important;
    }

    div[data-testid="column"]:has(button[kind="tertiary"]) button:hover,
    .stButton button[kind="tertiary"]:hover {
        background: transparent !important;
        color: var(--accent-dark) !important;
        text-decoration: underline;
        text-underline-offset: 0.35rem;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea {
        border-radius: 6px !important;
        background: rgba(255,255,255,0.92) !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 1.4rem;
        margin-top: 0.75rem;
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--muted);
        font-size: 1.05rem;
        font-weight: 850;
        padding-left: 0;
        padding-right: 0;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent-dark);
    }

    .section-note {
        color: var(--muted);
        font-size: 0.95rem;
        margin-top: -0.25rem;
        margin-bottom: 0.75rem;
    }

    [data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid var(--line);
    }

    div[data-testid="stImage"] img {
        border-radius: 8px;
        box-shadow: 0 10px 26px rgba(15, 127, 140, 0.12);
        aspect-ratio: 4 / 3;
        object-fit: cover;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 8px;
        box-shadow: 0 12px 28px rgba(15, 127, 140, 0.08);
    }

    .card-title {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.2rem;
        font-weight: 850;
        line-height: 1.15;
        margin-top: 0.25rem;
    }

    .card-meta {
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0.25rem 0 0.35rem;
    }

    .empty-panel {
        background: linear-gradient(135deg, #e6f6f8, #ffffff);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem;
    }

    .empty-panel-title {
        color: var(--accent-dark);
        font-weight: 900;
    }

    .empty-panel-copy {
        color: var(--muted);
        margin-top: 0.2rem;
    }

    .ranking-card {
        background:
            linear-gradient(90deg, rgba(255,255,255,0.94), rgba(255,255,255,0.76)),
            var(--ranking-image);
        background-position: center;
        background-size: cover;
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 12px 28px rgba(15, 127, 140, 0.08);
        margin-bottom: 0;
        min-height: 142px;
        overflow: hidden;
        padding: 1.1rem;
        position: relative;
    }

    .ranking-card:before {
        background: linear-gradient(90deg, rgba(255,255,255,0.96), rgba(255,255,255,0.82), rgba(255,255,255,0.58));
        content: "";
        inset: 0;
        position: absolute;
    }

    .ranking-card > * {
        position: relative;
        z-index: 1;
    }

    .ranking-card-title {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.35rem;
        font-weight: 850;
        line-height: 1.2;
    }

    .ranking-card-meta {
        color: var(--muted);
        font-size: 0.95rem;
        font-weight: 750;
        margin-top: 0.35rem;
    }

    .ranking-card-note {
        background: rgba(230, 246, 248, 0.9);
        border-radius: 8px;
        color: var(--accent-dark);
        font-size: 0.95rem;
        margin-top: 0.75rem;
        padding: 0.75rem;
    }

    .ranking-card-empty-note {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--muted);
        font-size: 0.92rem;
        margin-top: 0.65rem;
        padding: 0.65rem;
    }

    .ranking-badge {
        color: var(--accent);
        font-size: 0.8rem;
        font-weight: 900;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
    }

    .selected-panel {
        background: linear-gradient(135deg, #e6f6f8, #ffffff);
        border: 1px solid var(--line);
        border-radius: 8px;
        margin: 0.7rem 0 1rem;
        padding: 1rem;
    }

    .selected-panel-title {
        color: var(--accent-dark);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.45rem;
        font-weight: 850;
    }

    .selected-panel-copy {
        color: var(--muted);
        margin-top: 0.25rem;
    }

    div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stImage"]) {
        background: #ffffff;
        border-radius: 8px;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.25rem;
        margin: 2rem 0;
    }

    .feature-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 10px 28px rgba(38, 38, 38, 0.08);
        overflow: hidden;
    }

    .feature-image {
        background-position: center;
        background-size: cover;
        height: 160px;
    }

    .feature-body {
        padding: 1rem;
    }

    .feature-title {
        font-size: 1.05rem;
        font-weight: 850;
    }

    .feature-meta {
        color: var(--accent);
        font-size: 0.9rem;
        font-weight: 800;
        margin-top: 0.35rem;
    }

    .feature-copy {
        color: var(--muted);
        font-size: 0.92rem;
        margin-top: 0.45rem;
    }

    .restaurant-card-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }

    .restaurant-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 10px 26px rgba(15, 127, 140, 0.08);
        overflow: hidden;
    }

    .restaurant-photo {
        align-items: flex-end;
        background-position: center;
        background-size: cover;
        display: flex;
        height: 150px;
        padding: 0.9rem;
        position: relative;
    }

    .restaurant-photo:before {
        background: linear-gradient(180deg, rgba(0,0,0,0), rgba(5,24,36,0.78));
        content: "";
        inset: 0;
        position: absolute;
    }

    .restaurant-photo-title {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 900;
        line-height: 1.2;
        position: relative;
        z-index: 1;
    }

    .restaurant-card-body {
        padding: 0.9rem;
    }

    .restaurant-card-meta {
        color: var(--muted);
        display: flex;
        font-size: 0.9rem;
        font-weight: 700;
        justify-content: space-between;
    }

    .country-chip {
        align-items: center;
        background: var(--accent-soft);
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--accent-dark);
        display: inline-flex;
        font-size: 0.95rem;
        font-weight: 800;
        gap: 0.45rem;
        margin: 0.25rem 0 1rem;
        padding: 0.45rem 0.8rem;
    }

    .country-entry-panel {
        background: transparent;
        border: 0;
        box-shadow: none;
        margin: 0 0 0.85rem;
        padding: 0;
    }

    .country-button-title {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.4rem;
        font-weight: 900;
        margin-bottom: 0.3rem;
    }

    .country-entry-copy {
        color: var(--muted);
        font-size: 0.95rem;
        margin-bottom: 0.85rem;
    }

    div[data-testid="column"] div[data-testid="stButton"] > button {
        justify-content: center;
    }

    .flag {
        font-size: 1.15rem;
        line-height: 1;
    }

    @media (max-width: 760px) {
        .brand-title {
            font-size: 1.25rem;
        }

        .metric-grid {
            grid-template-columns: 1fr;
        }

        .feature-grid {
            grid-template-columns: 1fr;
        }

        .restaurant-card-grid {
            grid-template-columns: 1fr;
        }

        .hero {
            padding: 2.2rem 1.5rem;
        }

        .hero-title {
            font-size: 2.7rem;
        }

        .hero-search {
            align-items: stretch;
            flex-direction: column;
        }

        .hero-search-item {
            border-right: 0;
            border-bottom: 1px solid var(--line);
            padding-bottom: 0.75rem;
        }

    }
    </style>
    """,
    unsafe_allow_html=True,
)

header_columns = st.columns([0.06, 0.52, 0.1, 0.1, 0.12, 0.1], gap="small")
with header_columns[0]:
    st.markdown(
        """
        <div class="brand-mark" title="Food Atlas Boston">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" width="22" height="22">
                <circle cx="12" cy="12" r="8.5"></circle>
                <path d="M3.8 9h16.4"></path>
                <path d="M3.8 15h16.4"></path>
                <path d="M12 3.5a13 13 0 0 1 0 17"></path>
                <path d="M12 3.5a13 13 0 0 0 0 17"></path>
            </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_columns[1]:
    st.markdown(
        """
        <div class="brand-row">
            <div class="brand-title">Food Atlas Boston</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for column, view_name in zip(header_columns[2:], VIEW_OPTIONS):
    if column.button(VIEW_LABELS[view_name], key=f"top-nav-{view_name}", use_container_width=True, type="tertiary"):
        switch_view(view_name)
        st.rerun()

st.markdown(
    """
    <section class="hero">
        <div class="hero-kicker">Boston dining guide</div>
        <div class="hero-title">Find the places that taste like home.</div>
        <div class="hero-subtitle">
            Discover Boston restaurants by home cuisine, explore them on a map, and rate how authentic they feel.
        </div>
        <div class="hero-country-strip">
            <div class="hero-country-title">Start with where you are from</div>
            We use your home country to find restaurants from that cuisine and collect authenticity ratings from the right people.
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


def normalize_cuisines(cuisine_value):
    return {
        cuisine.strip().lower().replace(" ", "_")
        for cuisine in cuisine_value.replace(",", ";").split(";")
        if cuisine.strip()
    }


def country_for_cuisines(cuisines):
    for country, country_cuisines in COUNTRY_CUISINES.items():
        if cuisines & country_cuisines:
            return country
    return None


@st.cache_data(ttl=60 * 60 * 24)
def fetch_boston_restaurants():
    overpass_query = """
    [out:json][timeout:35];
    (
      node["amenity"~"^(restaurant|cafe|fast_food)$"]["name"]["cuisine"](around:25000,42.3601,-71.0589);
      way["amenity"~"^(restaurant|cafe|fast_food)$"]["name"]["cuisine"](around:25000,42.3601,-71.0589);
      relation["amenity"~"^(restaurant|cafe|fast_food)$"]["name"]["cuisine"](around:25000,42.3601,-71.0589);
    );
    out center 1500;
    """
    request = Request(
        OVERPASS_URL,
        data=urlencode({"data": overpass_query}).encode("utf-8"),
        headers={"User-Agent": "food-map-app/1.0"},
    )

    with urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    restaurants = []
    seen_names = set()
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        cuisine_text = tags.get("cuisine", "")
        if not name or name in seen_names or not cuisine_text:
            continue

        latitude = element.get("lat") or element.get("center", {}).get("lat")
        longitude = element.get("lon") or element.get("center", {}).get("lon")
        if latitude is None or longitude is None:
            continue

        cuisines = normalize_cuisines(cuisine_text)
        country = country_for_cuisines(cuisines)
        if country is None:
            continue

        restaurants.append(
            {
                "name": name,
                "country": country,
                "cuisine": ", ".join(sorted(cuisines)),
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        )
        seen_names.add(name)

    return sorted(restaurants, key=lambda restaurant: restaurant["name"])


def load_restaurants():
    try:
        restaurants = fetch_boston_restaurants()
        restaurants = merge_curated_restaurants(restaurants)
        if len(restaurants) >= 500:
            return restaurants, "OpenStreetMap"
        return restaurants + [
            restaurant
            for restaurant in FALLBACK_RESTAURANTS
            if restaurant["name"] not in {item["name"] for item in restaurants}
        ], "OpenStreetMap + sample fallback"
    except (URLError, TimeoutError, json.JSONDecodeError):
        return merge_curated_restaurants(FALLBACK_RESTAURANTS), "sample fallback"


def merge_curated_restaurants(restaurants):
    canonical_names = {
        "ittoku": "Izakaya Ittoku",
        "izakaya ittoku": "Izakaya Ittoku",
        "sugidama": "Sugidama Soba & Izakaya",
        "sugidama soba izakaya": "Sugidama Soba & Izakaya",
        "sugidama soba & izakaya": "Sugidama Soba & Izakaya",
        "café mami": "Cafe Mami",
        "cafe mami": "Cafe Mami",
        "yume ga arukara": "Yume Ga Arukara",
        "yume wo katare": "Yume Wo Katare",
    }
    curated_lookup = {
        restaurant["name"].strip().lower(): restaurant
        for restaurant in CURATED_MAJOR_RESTAURANTS
    }
    merged_restaurants = []
    for restaurant in restaurants:
        restaurant_copy = dict(restaurant)
        normalized_name = restaurant_copy["name"].strip().lower()
        if normalized_name in canonical_names:
            restaurant_copy["name"] = canonical_names[normalized_name]
            curated_restaurant = curated_lookup.get(restaurant_copy["name"].strip().lower())
            if curated_restaurant:
                restaurant_copy.update(curated_restaurant)
        merged_restaurants.append(restaurant_copy)

    deduped_restaurants = []
    existing_names = set()
    for restaurant in merged_restaurants:
        normalized_name = restaurant["name"].strip().lower()
        if normalized_name not in existing_names:
            deduped_restaurants.append(restaurant)
            existing_names.add(normalized_name)
    merged_restaurants = deduped_restaurants

    for restaurant in CURATED_MAJOR_RESTAURANTS:
        normalized_name = restaurant["name"].strip().lower()
        if normalized_name not in existing_names:
            merged_restaurants.append(dict(restaurant))
            existing_names.add(normalized_name)

    return sorted(merged_restaurants, key=lambda restaurant: restaurant["name"])


def get_query_param(name):
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def star_rating_html(ratings):
    if not ratings:
        average = 0
    else:
        average = sum(ratings) / len(ratings)

    stars = []
    for index in range(1, 6):
        if average >= index:
            stars.append('<span style="color:#facc15;">★</span>')
        elif average >= index - 0.5:
            stars.append(
                '<span style="background:linear-gradient(90deg,#facc15 50%,#cbd5e1 50%);'
                '-webkit-background-clip:text;background-clip:text;color:transparent;">★</span>'
            )
        else:
            stars.append('<span style="color:#cbd5e1;">★</span>')

    return "".join(stars)


def star_rating_text(ratings):
    if not ratings:
        return "☆☆☆☆☆"

    average = sum(ratings) / len(ratings)
    stars = []
    for index in range(1, 6):
        if average >= index:
            stars.append("★")
        elif average >= index - 0.5:
            stars.append("⯨")
        else:
            stars.append("☆")
    return "".join(stars)


def popup_html(restaurant, ratings):
    restaurant_name = html.escape(restaurant["name"])
    star_text = star_rating_html(ratings)
    review_count = len(ratings)
    if ratings:
        average_label = f"{sum(ratings) / len(ratings):.1f}"
    else:
        average_label = "New"

    return f"""
    <div style="font-family: Arial, sans-serif; min-width: 180px;">
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px;">{restaurant_name}</div>
        <div style="font-size: 18px; letter-spacing: 1px;">{star_text}</div>
        <div style="color:#64748b; font-size:12px; margin-top:6px;">{average_label} · {review_count} reviews</div>
        <div style="color:#075766; font-size:12px; font-weight:700; margin-top:6px;">Open Reviews for notes, or click the marker to rate.</div>
    </div>
    """


def restaurant_from_map_click(restaurants, click_data):
    if not click_data:
        return None

    clicked_latitude = click_data.get("lat")
    clicked_longitude = click_data.get("lng")
    if clicked_latitude is None or clicked_longitude is None:
        return None

    nearest_restaurant = min(
        restaurants,
        key=lambda restaurant: (
            abs(restaurant["latitude"] - clicked_latitude)
            + abs(restaurant["longitude"] - clicked_longitude)
        ),
        default=None,
    )
    if nearest_restaurant is None:
        return None

    distance = (
        abs(nearest_restaurant["latitude"] - clicked_latitude)
        + abs(nearest_restaurant["longitude"] - clicked_longitude)
    )
    if distance > 0.0005:
        return None

    return nearest_restaurant


def save_feedback(feedback):
    fieldnames = ["timestamp", "country", "topic", "restaurant", "message", "contact"]
    file_exists = os.path.exists(FEEDBACK_FILE)
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as feedback_file:
        writer = csv.DictWriter(feedback_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(feedback)


def get_setting(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def configured_review_form():
    action_url = get_setting("REVIEW_FORM_ACTION_URL")
    field_map = {
        "timestamp": get_setting("REVIEW_FORM_TIMESTAMP_FIELD"),
        "country": get_setting("REVIEW_FORM_COUNTRY_FIELD"),
        "restaurant": get_setting("REVIEW_FORM_RESTAURANT_FIELD"),
        "rating": get_setting("REVIEW_FORM_RATING_FIELD"),
        "note": get_setting("REVIEW_FORM_NOTE_FIELD"),
    }
    return action_url, field_map


def review_form_diagnostic(action_url, field_map):
    if not action_url:
        return "missing REVIEW_FORM_ACTION_URL"

    parsed_url = urlparse(action_url)
    public_form_url = "/forms/d/e/" in parsed_url.path and parsed_url.path.endswith("/formResponse")
    if not public_form_url:
        return "REVIEW_FORM_ACTION_URL should look like https://docs.google.com/forms/d/e/.../formResponse"

    missing_fields = [
        name
        for name, field_id in field_map.items()
        if not field_id
    ]
    if missing_fields:
        return f"missing field IDs: {', '.join(missing_fields)}"

    return "configured"


def send_review_to_google_form(review):
    action_url, field_map = configured_review_form()
    if not action_url or not all(field_map.values()):
        return False, "Review storage is not configured in Streamlit Secrets."

    diagnostic = review_form_diagnostic(action_url, field_map)
    if diagnostic != "configured":
        return False, diagnostic

    payload = {
        field_map["timestamp"]: review["timestamp"],
        field_map["country"]: review["country"],
        field_map["restaurant"]: review["restaurant"],
        field_map["rating"]: review["rating"],
        field_map["note"]: review["note"],
    }
    request = Request(
        action_url,
        data=urlencode(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "food-atlas-boston/1.0",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status in {200, 302}:
                return True, ""
            return False, f"Google Form returned status {response.status}."
    except Exception as error:
        if "HTTP Error 401" in str(error):
            return (
                False,
                "Google Form returned 401 Unauthorized. Open the form settings and turn off sign-in restrictions, "
                "email collection, and one-response limits; also confirm Secrets uses the /forms/d/e/.../formResponse URL.",
            )
        return False, f"Google Form submission failed: {error}"


def load_reviews_from_published_csv():
    csv_url = get_setting("REVIEW_SHEET_CSV_URL")
    if not csv_url:
        return None

    try:
        request = Request(csv_url, headers={"User-Agent": "food-atlas-boston/1.0"})
        with urlopen(request, timeout=10) as response:
            csv_text = response.read().decode("utf-8")
        return parse_review_csv(csv_text)
    except Exception:
        return None


def normalized_key(value):
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def first_value(row, candidates):
    normalized_row = {
        normalized_key(key): value
        for key, value in row.items()
    }
    for candidate in candidates:
        value = normalized_row.get(normalized_key(candidate))
        if value not in (None, ""):
            return value
    return ""


def parse_review_csv(csv_text):
    reviews = []
    for row in csv.DictReader(csv_text.splitlines()):
        restaurant = first_value(row, ["restaurant", "レストラン", "店", "店舗"])
        rating = first_value(row, ["rating", "score", "your rating", "評価", "採点"])
        if not restaurant or not rating:
            continue

        try:
            rating_value = float(rating)
        except ValueError:
            continue

        reviews.append(
            {
                "timestamp": first_value(row, ["timestamp", "time", "日時", "タイムスタンプ"]),
                "country": first_value(row, ["country", "home country", "国", "出身国"]),
                "restaurant": restaurant,
                "rating": rating_value,
                "note": first_value(row, ["note", "notes", "comment", "備考", "コメント"]),
            }
        )
    return reviews


def save_review(review):
    sent_to_google_form, error_message = send_review_to_google_form(review)
    if sent_to_google_form:
        return True, ""

    fieldnames = ["timestamp", "country", "restaurant", "rating", "note"]
    file_exists = os.path.exists(REVIEWS_FILE)
    with open(REVIEWS_FILE, "a", newline="", encoding="utf-8") as reviews_file:
        writer = csv.DictWriter(reviews_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(review)
    return False, error_message


def load_reviews():
    published_reviews = load_reviews_from_published_csv()
    if published_reviews is not None:
        return published_reviews

    if not os.path.exists(REVIEWS_FILE):
        return []
    with open(REVIEWS_FILE, "r", encoding="utf-8") as reviews_file:
        return [
            {
                "timestamp": row.get("timestamp", ""),
                "country": row.get("country", ""),
                "restaurant": row.get("restaurant", ""),
                "rating": float(row.get("rating", 0) or 0),
                "note": row.get("note", ""),
            }
            for row in csv.DictReader(reviews_file)
            if row.get("restaurant") and row.get("rating")
        ]


def configured_google_form():
    action_url = get_setting("FEEDBACK_FORM_ACTION_URL") or get_setting("GOOGLE_FORM_ACTION_URL")
    field_map = {
        "topic": get_setting("FEEDBACK_FORM_TOPIC_FIELD") or get_setting("GOOGLE_FORM_TOPIC_FIELD"),
        "country": get_setting("FEEDBACK_FORM_COUNTRY_FIELD") or get_setting("GOOGLE_FORM_COUNTRY_FIELD"),
        "restaurant": get_setting("FEEDBACK_FORM_RESTAURANT_FIELD") or get_setting("GOOGLE_FORM_RESTAURANT_FIELD"),
        "message": get_setting("FEEDBACK_FORM_MESSAGE_FIELD") or get_setting("GOOGLE_FORM_MESSAGE_FIELD"),
        "contact": get_setting("FEEDBACK_FORM_CONTACT_FIELD") or get_setting("GOOGLE_FORM_CONTACT_FIELD"),
    }
    return action_url, field_map


def send_feedback_to_google_form(feedback):
    action_url, field_map = configured_google_form()
    if not action_url or not all(field_map.values()):
        return False

    payload = {
        field_map["topic"]: feedback["topic"],
        field_map["country"]: feedback["country"],
        field_map["restaurant"]: feedback["restaurant"],
        field_map["message"]: feedback["message"],
        field_map["contact"]: feedback["contact"],
    }
    request = Request(
        action_url,
        data=urlencode(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "food-atlas-boston/1.0",
        },
    )
    try:
        with urlopen(request, timeout=10):
            return True
    except Exception:
        return False


if st.session_state.get("data_version") != DATA_VERSION:
    st.session_state.all_restaurants, st.session_state.data_source = load_restaurants()
    st.session_state.data_version = DATA_VERSION

st.session_state.reviews = load_reviews()

if "feedback" not in st.session_state:
    st.session_state.feedback = []

all_restaurants = st.session_state.all_restaurants

total_reviews = len(st.session_state.reviews)

country_options = sorted(COUNTRY_CUISINES)
view_options = VIEW_OPTIONS

with st.container(border=True):
    st.markdown(
        """
        <div class="country-entry-panel">
            <div class="country-button-title">Where are you from?</div>
            <div class="country-entry-copy">Start with your home country. We will show restaurants from that cuisine and collect authenticity ratings from people who know it best.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    country_query = st.text_input("Home country", placeholder="Try Japan, Italy, Mexico...")
    country_query_normalized = country_query.strip().lower()
    inferred_countries = [
        country
        for country in country_options
        if country_query_normalized and country_query_normalized in country.lower()
    ]
    if not inferred_countries:
        inferred_countries = country_options

    inferred_default_index = (
        inferred_countries.index(st.session_state.get("selected_country", "Japan"))
        if st.session_state.get("selected_country", "Japan") in inferred_countries
        else 0
    )
    inferred_country = st.selectbox(
        "Home country match",
        inferred_countries,
        index=inferred_default_index,
        format_func=lambda country: f"{COUNTRY_FLAGS.get(country, '')} {country}",
    )
    st.session_state.selected_country = inferred_country

st.markdown(
    f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">Restaurants</div>
            <div class="metric-value">{len(all_restaurants)}</div>
            <div class="metric-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 21h18"/>
                    <path d="M5 21V8l7-5 7 5v13"/>
                    <path d="M9 21v-7h6v7"/>
                </svg>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Countries</div>
            <div class="metric-value">{len(COUNTRY_CUISINES)}</div>
            <div class="metric-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"/>
                    <path d="M3.6 9h16.8"/>
                    <path d="M3.6 15h16.8"/>
                    <path d="M12 3a14 14 0 0 1 0 18"/>
                    <path d="M12 3a14 14 0 0 0 0 18"/>
                </svg>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Ratings</div>
            <div class="metric-value">{total_reviews}</div>
            <div class="metric-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.8 1-6.1-4.4-4.3 6.1-.9L12 3z"/>
                </svg>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
origin_country = st.session_state.get("selected_country", "Japan")
country_restaurants = [
    restaurant
    for restaurant in all_restaurants
    if restaurant["country"] == origin_country
]
origin_flag = COUNTRY_FLAGS.get(origin_country, "")
st.markdown(
    f'<div class="country-chip"><span class="flag">{origin_flag}</span><span>Showing restaurants for {html.escape(origin_country)} cuisine authenticity</span></div>',
    unsafe_allow_html=True,
)

selected_from_map = st.session_state.get("map_selected_restaurant") or get_query_param("selected")
selected_from_map_restaurant = next(
    (
        restaurant
        for restaurant in country_restaurants
        if restaurant["name"] == selected_from_map
    ),
    None,
)


def render_rate_view():
    st.markdown(f'<div id="{RATING_FORM_ANCHOR}"></div>', unsafe_allow_html=True)
    st.subheader("Rate Authenticity")
    st.markdown(
        f'<p class="section-note"><span class="flag">{origin_flag}</span> {len(country_restaurants)} {origin_country} cuisine restaurants near Boston.</p>',
        unsafe_allow_html=True,
    )
    action_url, field_map = configured_review_form()
    if not action_url or not all(field_map.values()):
        st.warning("Review storage is not fully configured. Ratings will not persist after app restart until Streamlit Secrets are completed.")
    elif review_form_diagnostic(action_url, field_map) != "configured":
        st.warning(review_form_diagnostic(action_url, field_map))

    selected_restaurant = selected_from_map_restaurant
    if selected_restaurant:
        st.markdown(
            f"""
            <div class="selected-panel">
                <div class="selected-panel-title">{origin_flag} {html.escape(selected_restaurant["name"])}</div>
                <div class="selected-panel-copy">Opened from the restaurant card or map. Add your authenticity rating below.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    restaurant_query = st.text_input(
        "Search restaurants",
        value=selected_restaurant["name"] if selected_restaurant else "",
        placeholder="Type a restaurant name...",
    )
    query = restaurant_query.strip().lower()
    matching_restaurants = [
        restaurant
        for restaurant in country_restaurants
        if query and query in restaurant["name"].lower()
    ]

    if selected_from_map and selected_from_map_restaurant is None:
        st.info("Select the matching home country to rate the restaurant you opened from the map.")

    if matching_restaurants:
        selected_name = st.selectbox(
            "Matching restaurants",
            [restaurant["name"] for restaurant in matching_restaurants],
            index=0,
        )
        selected_restaurant = next(
            restaurant for restaurant in matching_restaurants if restaurant["name"] == selected_name
        )
    elif query:
        st.warning("No matching restaurants found.")

    if selected_restaurant:
        user_rating = st.slider("Your rating", 1.0, 5.0, 4.0, 0.5)
        note = st.text_area("Note optional")

        if st.button("Submit Rating", use_container_width=True):
            review_record = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "country": origin_country,
                "restaurant": selected_restaurant["name"],
                "rating": user_rating,
                "note": note.strip(),
            }
            st.session_state.reviews.append(review_record)
            sent_to_google_form, error_message = save_review(review_record)
            if sent_to_google_form:
                st.success(f"Thanks for rating {selected_restaurant['name']}.")
            else:
                st.error("The review was not saved to Google Forms yet.")
                st.caption(error_message)
                st.warning("Check Streamlit Secrets and the Google Form field IDs. A local backup was saved only for this runtime.")
    else:
        st.markdown(
            """
            <div class="empty-panel">
                <div class="empty-panel-title">Choose a restaurant to rate.</div>
                <div class="empty-panel-copy">Search here, or press Rate from any restaurant card.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

filtered_reviews = [
    review
    for review in st.session_state.reviews
    if review["country"] == origin_country
]

average_by_restaurant = {}
for review in filtered_reviews:
    average_by_restaurant.setdefault(review["restaurant"], []).append(review["rating"])

reviews_by_restaurant = {}
for review in filtered_reviews:
    reviews_by_restaurant.setdefault(review["restaurant"], []).append(review)

average_rows = [
    {
        "Restaurant": restaurant,
        "Average Rating": round(sum(ratings) / len(ratings), 2),
        "Reviews": len(ratings),
    }
    for restaurant, ratings in sorted(
        average_by_restaurant.items(),
        key=lambda item: (
            -(sum(item[1]) / len(item[1])),
            -len(item[1]),
            item[0],
        ),
    )
]

def restaurant_summary_row(restaurant):
    ratings = average_by_restaurant.get(restaurant["name"], [])
    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    return {
        "Restaurant": f"{origin_flag} {restaurant['name']}",
        "Average Rating": average_rating if average_rating is not None else "Not rated",
        "Reviews": len(ratings),
    }


RESTAURANT_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1551218808-94e220e084d2?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1533777324565-a040eb52fac1?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1544148103-0773bf10d330?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80",
]


def restaurant_image_url(restaurant_name):
    image_index = sum(ord(character) for character in restaurant_name) % len(RESTAURANT_IMAGE_URLS)
    return RESTAURANT_IMAGE_URLS[image_index]


def render_restaurant_cards(restaurants, start_index=0, key_prefix="restaurant", columns_per_row=3):
    if not restaurants:
        return

    for row_start in range(0, len(restaurants), columns_per_row):
        columns = st.columns(columns_per_row)
        for offset, restaurant in enumerate(restaurants[row_start:row_start + columns_per_row]):
            index = start_index + row_start + offset
            ratings = average_by_restaurant.get(restaurant["name"], [])
            average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
            rating_label = f"{average_rating:.2f}" if average_rating is not None else "New"
            review_label = f"{len(ratings)} review" if len(ratings) == 1 else f"{len(ratings)} reviews"

            with columns[offset]:
                with st.container(border=True):
                    st.image(RESTAURANT_IMAGE_URLS[index % len(RESTAURANT_IMAGE_URLS)], use_container_width=True)
                    st.markdown(
                        f'<div class="card-title">{origin_flag} {html.escape(restaurant["name"])}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="card-meta">{star_rating_text(ratings)} · {rating_label} · {review_label}</div>',
                        unsafe_allow_html=True,
                    )
                    safe_name = restaurant["name"].strip().lower().replace(" ", "-")
                    if st.button("Rate", key=f"{key_prefix}-rate-card-{index}-{safe_name}", use_container_width=True):
                        st.session_state.map_selected_restaurant = restaurant["name"]
                        st.session_state.active_view = "Rate"
                        st.rerun()


def ranked_restaurant_entries(restaurants):
    ranked_entries = []
    previous_average = None
    previous_rank = 0
    for position, restaurant in enumerate(restaurants, start=1):
        ratings = average_by_restaurant.get(restaurant["name"], [])
        if not ratings:
            continue

        average_rating = round(sum(ratings) / len(ratings), 2)
        if previous_average is not None and average_rating == previous_average:
            rank = previous_rank
        else:
            rank = position
            previous_average = average_rating
            previous_rank = rank

        ranked_entries.append(
            {
                "rank": rank,
                "restaurant": restaurant,
                "ratings": ratings,
                "average_rating": average_rating,
                "notes": [
                    review.get("note", "").strip()
                    for review in reviews_by_restaurant.get(restaurant["name"], [])
                    if review.get("note", "").strip()
                ],
            }
        )

    return ranked_entries


def render_ranking_cards(entries):
    if not entries:
        return

    for entry in entries:
        restaurant = entry["restaurant"]
        ratings = entry["ratings"]
        notes = entry["notes"]
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="ranking-card" style="--ranking-image: url('{restaurant_image_url(restaurant["name"])}')" title="{html.escape(notes[-1] if notes else 'No notes yet.')}">
                    <div class="ranking-badge">#{entry["rank"]} most authentic</div>
                    <div class="ranking-card-title">{origin_flag} {html.escape(restaurant["name"])}</div>
                    <div class="ranking-card-meta">{star_rating_html(ratings)} · {entry["average_rating"]:.1f} average · {len(ratings)} reviews</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if notes:
                with st.expander("See reviews"):
                    for note in notes:
                        st.markdown(
                            f'<div class="ranking-card-note">"{html.escape(note)}"</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    '<div class="ranking-card-empty-note">No written review yet.</div>',
                    unsafe_allow_html=True,
                )


sorted_country_restaurants = sorted(
    country_restaurants,
    key=lambda restaurant: (
        -(sum(average_by_restaurant.get(restaurant["name"], [])) / len(average_by_restaurant.get(restaurant["name"], []))
          if average_by_restaurant.get(restaurant["name"], []) else 0),
        -len(average_by_restaurant.get(restaurant["name"], [])),
        CURATED_PRIORITY.get(restaurant["name"].strip().lower(), 9999),
        restaurant["name"],
    ),
)
restaurant_rows = [
    restaurant_summary_row(restaurant)
    for restaurant in sorted_country_restaurants
]


def render_explore_view():
    st.subheader("Explore Restaurants")
    map_area, list_area = st.columns([0.56, 0.44], gap="large")

    with map_area:
        st.markdown('<div id="map-section"></div>', unsafe_allow_html=True)
        st.subheader("Map")
        restaurant_map = folium.Map(location=BOSTON_CENTER, zoom_start=12, tiles="CartoDB positron")
        for restaurant in country_restaurants:
            ratings = average_by_restaurant.get(restaurant["name"], [])
            folium.CircleMarker(
                location=[restaurant["latitude"], restaurant["longitude"]],
                radius=7,
                color="#075766",
                fill=True,
                fill_color="#0f7f8c",
                fill_opacity=0.9,
                popup=folium.Popup(popup_html(restaurant, ratings), max_width=260),
                tooltip=(
                    f"{html.escape(restaurant['name'])} · "
                    f"{star_rating_text(ratings)} · "
                    f"{len(ratings)} reviews · Open Reviews"
                ),
            ).add_to(restaurant_map)

        map_data = st_folium(restaurant_map, width=640, height=520)
        clicked_restaurant = restaurant_from_map_click(
            country_restaurants,
            map_data.get("last_object_clicked") if map_data else None,
        )
        if clicked_restaurant and st.session_state.get("map_selected_restaurant") != clicked_restaurant["name"]:
            st.session_state.map_selected_restaurant = clicked_restaurant["name"]
            st.session_state.active_view = "Rate"
            st.rerun()

    with list_area:
        selected_map_name = st.session_state.get("map_selected_restaurant")
        if selected_map_name:
            st.success(f"{selected_map_name} is selected. The rating form is ready.")

        top_rated_rows = [
            restaurant
            for restaurant in sorted_country_restaurants
            if len(average_by_restaurant.get(restaurant["name"], [])) > 0
        ][:5]
        st.subheader("Popular with Locals")
        if top_rated_rows:
            render_restaurant_cards(top_rated_rows[:3], key_prefix="popular", columns_per_row=1)
        else:
            st.markdown(
                """
                <div class="empty-panel">
                    <div class="empty-panel-title">No local ratings yet.</div>
                    <div class="empty-panel-copy">A few high-priority places are shown below so the first reviews can shape the ranking.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_restaurant_cards(sorted_country_restaurants[:3], key_prefix="popular-empty", columns_per_row=1)


    st.markdown('<div id="restaurants-section"></div>', unsafe_allow_html=True)
    st.subheader(f"{origin_country} Restaurants")
    st.markdown(
        f'<p class="section-note">{len(country_restaurants)} places found. Top rated restaurants appear first, then places with more reviews.</p>',
        unsafe_allow_html=True,
    )
    render_restaurant_cards(sorted_country_restaurants[:12], key_prefix="list")
    if len(sorted_country_restaurants) > 12:
        with st.expander("Show more restaurants"):
            render_restaurant_cards(sorted_country_restaurants[12:48], start_index=12, key_prefix="more")


def render_reviews_view():
    st.markdown('<div id="reviews-section"></div>', unsafe_allow_html=True)
    st.subheader("Reviews")
    st.markdown(
        f'<p class="section-note">See which {origin_flag} {html.escape(origin_country)} restaurants feel most authentic to people from that home cuisine.</p>',
        unsafe_allow_html=True,
    )

    if average_rows:
        st.subheader("Most Authentic Right Now")
        ranked_restaurants = [
            restaurant
            for restaurant in sorted_country_restaurants
            if average_by_restaurant.get(restaurant["name"])
        ]
        ranked_entries = ranked_restaurant_entries(ranked_restaurants)
        render_ranking_cards(ranked_entries[:5])
        if len(ranked_entries) > 5:
            with st.expander("Show more"):
                render_ranking_cards(ranked_entries[5:])
    else:
        st.markdown(
            """
            <div class="empty-panel">
                <div class="empty-panel-title">No ratings yet.</div>
                <div class="empty-panel-copy">Use Explore or Rate to add the first authenticity score.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if get_setting("REVIEW_SHEET_CSV_URL"):
            st.caption("If your Google Sheet already has responses, make sure the response Sheet is shared or published so the app can read its CSV URL.")


def render_feedback_view():
    st.markdown('<div id="feedback-section"></div>', unsafe_allow_html=True)
    st.subheader("Send Feedback")
    st.markdown(
        '<p class="section-note">Found a duplicate, wrong cuisine, missing restaurant, or map issue? Send it to the team.</p>',
        unsafe_allow_html=True,
    )
    with st.form("feedback_form"):
        feedback_topic = st.selectbox(
            "Issue type",
            [
                "Duplicate restaurant",
                "Wrong cuisine or country",
                "Missing restaurant",
                "Map location issue",
                "Other",
            ],
        )
        feedback_restaurant = st.text_input("Restaurant name optional")
        feedback_message = st.text_area("What should we fix?")
        feedback_contact = st.text_input("Email optional")
        feedback_submitted = st.form_submit_button("Send Feedback")

        if feedback_submitted:
            if feedback_message.strip():
                feedback_record = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "country": origin_country,
                    "topic": feedback_topic,
                    "restaurant": feedback_restaurant.strip(),
                    "message": feedback_message.strip(),
                    "contact": feedback_contact.strip(),
                }
                st.session_state.feedback.append(feedback_record)
                save_feedback(feedback_record)
                sent_to_google = send_feedback_to_google_form(feedback_record)
                if sent_to_google:
                    st.success("Thanks. Your feedback has been sent to the team.")
                else:
                    st.success("Thanks. Your feedback has been saved for the team.")
                    st.caption("Google Form delivery is not configured yet, so this prototype kept a local backup.")
            else:
                st.error("Please describe what should be fixed.")


if st.session_state.active_view == "Rate":
    render_rate_view()
elif st.session_state.active_view == "Reviews":
    render_reviews_view()
elif st.session_state.active_view == "Feedback":
    render_feedback_view()
else:
    render_explore_view()
