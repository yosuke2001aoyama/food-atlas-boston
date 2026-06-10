import csv
import html
import json
import os
import re
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
APP_NAME = "HomeTaste Boston"
DATA_VERSION = "hometaste-boston-v1"
RATING_FORM_ANCHOR = "rate-restaurant"
FEEDBACK_FILE = "feedback.csv"
REVIEWS_FILE = "reviews.csv"

RELATIONSHIP_WEIGHTS = {
    "I grew up with this cuisine": 1.0,
    "My family cooks this cuisine": 0.9,
    "I lived in this country/region for 3+ years": 0.8,
    "I lived there for 1-3 years": 0.6,
    "I speak the language and regularly eat this cuisine": 0.5,
    "I'm a fan and want to leave a general dining note": 0.1,
}

LIVED_EXPERIENCE_RELATIONSHIPS = {
    relationship
    for relationship, weight in RELATIONSHIP_WEIGHTS.items()
    if weight >= 0.5
}

DIMENSION_FIELDS = [
    ("ingredient_score", "Ingredients"),
    ("people_language_score", "People / language"),
    ("regional_specificity_score", "Regional specificity"),
    ("reminds_home_score", "Reminds me of home"),
]

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
        "ice_cream",
        "juice",
        "regional",
        "sandwich",
        "steak_house",
        "wings",
    },
    "Vietnam": {"vietnamese", "pho"},
}

FALLBACK_RESTAURANTS = [
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
    {"name": "O Ya", "country": "Japan", "cuisine": "japanese, omakase", "latitude": 42.35110, "longitude": -71.05685},
    {"name": "Avana Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35224, "longitude": -71.06074},
    {"name": "Avana Sushi III", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.34850, "longitude": -71.08290},
    {"name": "Blue Fuji", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.42080, "longitude": -71.10560},
    {"name": "Basho", "country": "Japan", "cuisine": "japanese", "latitude": 42.34629, "longitude": -71.09868},
    {"name": "Bosso Ramen Tavern", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.35010, "longitude": -71.08150},
    {"name": "Dabin", "country": "Japan", "cuisine": "japanese, sushi", "latitude": 42.43112, "longitude": -71.10769},
    {"name": "Daikanyama", "country": "Japan", "cuisine": "japanese, sushi", "latitude": 42.34990, "longitude": -71.08120},
    {"name": "Ebi Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.38720, "longitude": -71.10040},
    {"name": "Fuji at Kendall", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.36360, "longitude": -71.08120},
    {"name": "Fuji at HSP", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35380, "longitude": -71.04760},
    {"name": "Genki Ya Brookline", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.34280, "longitude": -71.12170},
    {"name": "Gyu-Kaku Japanese BBQ", "country": "Japan", "cuisine": "japanese, bbq", "latitude": 42.35171, "longitude": -71.06437},
    {"name": "Isshindo Ramen", "country": "Japan", "cuisine": "ramen, japanese", "latitude": 42.34870, "longitude": -71.08220},
    {"name": "Laughing Monk Cafe", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.33330, "longitude": -71.10470},
    {"name": "Mad Monkfish", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.36370, "longitude": -71.10180},
    {"name": "Matsunori Handroll Bar", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35020, "longitude": -71.08190},
    {"name": "Oppa Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35000, "longitude": -71.13110},
    {"name": "Pagu", "country": "Japan", "cuisine": "japanese, spanish", "latitude": 42.36170, "longitude": -71.09750},
    {"name": "Sakana Sushi", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.37220, "longitude": -71.12100},
    {"name": "Sakura Japanese", "country": "Japan", "cuisine": "sushi, japanese", "latitude": 42.35840, "longitude": -71.05890},
    {"name": "Shabu-Zen", "country": "Japan", "cuisine": "japanese, hot pot", "latitude": 42.35050, "longitude": -71.06110},
    {"name": "Shiki", "country": "Japan", "cuisine": "japanese", "latitude": 42.34430, "longitude": -71.12380},
    {"name": "Tsurutontan Udon Noodle Brasserie", "country": "Japan", "cuisine": "udon, japanese", "latitude": 42.34955, "longitude": -71.08168},
    {"name": "Umami Omakase", "country": "Japan", "cuisine": "japanese, omakase", "latitude": 42.34440, "longitude": -71.12440},
    {"name": "Wa Shin", "country": "Japan", "cuisine": "japanese, omakase", "latitude": 42.35110, "longitude": -71.07720},
]

CURATED_PRIORITY = {
    restaurant["name"].strip().lower(): index
    for index, restaurant in enumerate(CURATED_MAJOR_RESTAURANTS)
}


st.set_page_config(page_title=APP_NAME, layout="wide")

VIEW_OPTIONS = ["Explore", "Check", "Voices", "Report"]
TOP_NAV_OPTIONS = VIEW_OPTIONS
VIEW_LABELS = {
    "Explore": "Explore",
    "Check": "Add a Check",
    "Voices": "Voices",
    "Report": "Report issue",
}
initial_view = st.query_params.get("view")
if isinstance(initial_view, list):
    initial_view = initial_view[0] if initial_view else None
legacy_view_aliases = {
    "Rate": "Check",
    "Reviews": "Voices",
    "Feedback": "Report",
}
initial_view = legacy_view_aliases.get(initial_view, initial_view)
if initial_view in VIEW_OPTIONS:
    st.session_state.active_view = initial_view
elif "active_view" not in st.session_state:
    st.session_state.active_view = "Explore"
initial_menu = st.query_params.get("menu")
if isinstance(initial_menu, list):
    initial_menu = initial_menu[0] if initial_menu else None
if "menu_open" not in st.session_state:
    st.session_state.menu_open = initial_menu == "open"


def switch_view(view_name):
    st.session_state.active_view = view_name


def open_check_for_restaurant(restaurant_name):
    st.session_state.map_selected_restaurant = restaurant_name
    st.session_state.check_dialog_open = True


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
        padding-top: 2.4rem;
        padding-bottom: 3rem;
    }

    .site-header {
        align-items: center;
        display: flex;
        gap: 1.5rem;
        justify-content: space-between;
        margin: 0 0 1.7rem;
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
        gap: 1.1rem;
        min-width: 0;
    }

    .brand-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 2.15rem;
        font-weight: 800;
        line-height: 1;
        white-space: nowrap;
    }

    .brand-mark {
        align-items: center;
        background: transparent;
        border: 0;
        border-radius: 999px;
        color: var(--accent-dark);
        display: inline-flex;
        font-size: 1.45rem;
        height: 38px;
        justify-content: center;
        text-decoration: none;
        width: 38px;
    }

    .brand-mark:hover {
        color: var(--accent);
        transform: translateY(-1px);
    }

    .top-nav-links {
        align-items: center;
        display: flex;
        gap: clamp(1.25rem, 4vw, 3rem);
        justify-content: flex-end;
    }

    .top-nav-links a {
        border-bottom: 1px solid transparent;
        color: var(--muted);
        font-size: 1rem;
        font-weight: 800;
        padding: 0.25rem 0;
        text-decoration: none;
    }

    .top-nav-links a:hover,
    .top-nav-links a.active {
        border-bottom-color: var(--accent);
        color: var(--accent-dark);
    }

    .feedback-cta {
        align-items: center;
        background: linear-gradient(135deg, rgba(244,239,227,0.92), rgba(255,255,255,0.8));
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--muted);
        display: flex;
        gap: 0.75rem;
        justify-content: space-between;
        margin: 0.25rem 0 1.5rem;
        padding: 0.8rem 1rem;
    }

    .feedback-cta strong {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
    }

    .feedback-cta a {
        color: var(--accent-dark);
        font-weight: 850;
        text-decoration: none;
    }

    .feedback-cta a:hover {
        text-decoration: underline;
        text-underline-offset: 0.25rem;
    }

    section[data-testid="stSidebar"] {
        background: rgba(251,250,246,0.97);
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] .side-nav-link {
        border-bottom: 1px solid rgba(222,214,199,0.65);
        color: var(--muted);
        display: block;
        font-size: 1.05rem;
        font-weight: 800;
        padding: 0.85rem 0;
        text-decoration: none;
    }

    section[data-testid="stSidebar"] .side-nav-link:hover,
    section[data-testid="stSidebar"] .side-nav-link.active {
        color: var(--accent-dark);
    }

    section[data-testid="stSidebar"] .side-nav-link.subtle {
        color: var(--muted);
        font-size: 0.92rem;
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

    .about-panel {
        background: linear-gradient(135deg, rgba(244,239,227,0.92), rgba(255,255,255,0.86));
        border: 1px solid var(--line);
        border-radius: 8px;
        margin: 1.25rem 0 1.25rem;
        padding: 1.1rem 1.25rem;
    }

    .about-eyebrow {
        color: var(--accent-dark);
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.25rem;
        font-weight: 850;
        margin-bottom: 0.35rem;
    }

    .about-copy {
        color: var(--muted);
        font-size: 0.98rem;
        line-height: 1.65;
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

    div[data-testid="stSegmentedControl"] {
        justify-content: flex-end;
    }

    div[data-testid="stSegmentedControl"] label {
        background: transparent !important;
        border: 0 !important;
        color: var(--muted) !important;
        font-size: 1.02rem !important;
        font-weight: 750 !important;
        padding: 0.35rem 0.45rem !important;
    }

    div[data-testid="stSegmentedControl"] label[data-baseweb="radio"] {
        box-shadow: none !important;
    }

    div[data-testid="stSegmentedControl"] label[aria-checked="true"],
    div[data-testid="stSegmentedControl"] label:hover {
        color: var(--accent-dark) !important;
        text-decoration: underline;
        text-underline-offset: 0.35rem;
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

    .leaflet-control-attribution {
        font-size: 9px !important;
        opacity: 0.58 !important;
        transform: scale(0.78);
        transform-origin: bottom right;
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

    [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid var(--line) !important;
        border-radius: 6px !important;
        box-shadow: 0 8px 24px rgba(23, 32, 45, 0.045);
        margin-bottom: 0.65rem;
        overflow: hidden;
    }

    [data-testid="stExpander"] summary {
        color: var(--ink);
        font-weight: 780;
        letter-spacing: 0;
        padding: 0.25rem 0.2rem;
    }

    [data-testid="stExpander"] summary:hover {
        color: var(--accent-dark);
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
        background-color: #d8d0c0;
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

    .signal-row {
        color: var(--accent-dark);
        font-size: 0.9rem;
        font-weight: 800;
        margin-top: 0.55rem;
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
        .site-header {
            align-items: flex-start;
            flex-direction: column;
            gap: 1rem;
        }

        .brand-title {
            font-size: 1.25rem;
        }

        .top-nav-links {
            gap: 1rem;
            justify-content: flex-start;
        }

        .feedback-cta {
            align-items: flex-start;
            flex-direction: column;
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

active_view = st.session_state.active_view
header_columns = st.columns([0.06, 0.44, 0.12, 0.14, 0.11, 0.13], gap="small")
with header_columns[0]:
    if st.button("🌐", key="menu-toggle", help="Open or close menu", type="tertiary"):
        st.session_state.menu_open = not st.session_state.menu_open
        st.rerun()

with header_columns[1]:
    st.markdown(
        f"""
        <div class="brand-row">
            <div class="brand-title">{APP_NAME}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for nav_column, view_name in zip(header_columns[2:], TOP_NAV_OPTIONS):
    with nav_column:
        label = VIEW_LABELS[view_name]
        if active_view == view_name:
            label = f"• {label}"
        if st.button(label, key=f"top-nav-{view_name}", type="tertiary", use_container_width=True):
            switch_view(view_name)
            st.rerun()

if st.session_state.menu_open:
    with st.sidebar:
        st.markdown(f"## {APP_NAME}")
        st.markdown("Jump to a section.")
        for view_name in VIEW_OPTIONS:
            label = VIEW_LABELS[view_name]
            if active_view == view_name:
                label = f"• {label}"
            if st.button(label, key=f"side-nav-{view_name}", type="tertiary", use_container_width=True):
                switch_view(view_name)
                st.rerun()
        if st.button("Close menu", key="side-close-menu", type="tertiary", use_container_width=True):
            st.session_state.menu_open = False
            st.rerun()

st.markdown(
    """
    <section class="hero">
        <div class="hero-kicker">Boston dining guide</div>
        <div class="hero-title">HomeTaste Boston</div>
        <div class="hero-subtitle">
            Find the places that taste like home — to someone.
        </div>
        <div class="hero-country-strip">
            <div class="hero-country-title">A restaurant map shaped by lived experience</div>
            Most restaurant apps show what’s popular. HomeTaste helps you discover restaurants through people who know the cuisine from lived experience.
            Anyone can explore. People with lived experience can add HomeTaste checks.
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
        "izakayaittoku": "Izakaya Ittoku",
        "sugidama": "Sugidama Soba & Izakaya",
        "sugidama soba izakaya": "Sugidama Soba & Izakaya",
        "sugidama soba & izakaya": "Sugidama Soba & Izakaya",
        "sugidamasobaizakaya": "Sugidama Soba & Izakaya",
        "café mami": "Cafe Mami",
        "cafe mami": "Cafe Mami",
        "cafemami": "Cafe Mami",
        "yume ga arukara": "Yume Ga Arukara",
        "yume wo katare": "Yume Wo Katare",
    }

    def restaurant_name_key(name):
        return re.sub(r"[^a-z0-9]", "", name.strip().lower())

    curated_lookup = {
        restaurant["name"].strip().lower(): restaurant
        for restaurant in CURATED_MAJOR_RESTAURANTS
    }
    merged_restaurants = []
    for restaurant in restaurants:
        restaurant_copy = dict(restaurant)
        normalized_name = restaurant_copy["name"].strip().lower()
        normalized_key = restaurant_name_key(restaurant_copy["name"])
        if normalized_name in canonical_names:
            restaurant_copy["name"] = canonical_names[normalized_name]
        elif normalized_key in canonical_names:
            restaurant_copy["name"] = canonical_names[normalized_key]
        if restaurant_copy["name"].strip().lower() in canonical_names:
            restaurant_copy["name"] = canonical_names[restaurant_copy["name"].strip().lower()]
        if restaurant_copy["name"].strip().lower() != normalized_name:
            curated_restaurant = curated_lookup.get(restaurant_copy["name"].strip().lower())
            if curated_restaurant:
                restaurant_copy.update(curated_restaurant)
        merged_restaurants.append(restaurant_copy)

    deduped_restaurants = []
    existing_names = set()
    for restaurant in merged_restaurants:
        normalized_name = restaurant_name_key(restaurant["name"])
        if normalized_name not in existing_names:
            deduped_restaurants.append(restaurant)
            existing_names.add(normalized_name)
    merged_restaurants = deduped_restaurants

    for restaurant in CURATED_MAJOR_RESTAURANTS:
        normalized_name = restaurant_name_key(restaurant["name"])
        if normalized_name not in existing_names:
            merged_restaurants.append(dict(restaurant))
            existing_names.add(normalized_name)

    return sorted(merged_restaurants, key=lambda restaurant: restaurant["name"])


def get_query_param(name):
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def cuisine_label(country):
    labels = {
        "China / Taiwan / Hong Kong": "Chinese / Taiwanese / Hong Kong",
        "United States": "American",
        "United Kingdom": "British",
    }
    if country in labels:
        return labels[country]
    if country.endswith("y"):
        return f"{country[:-1]}ian"
    if country.endswith("a"):
        return f"{country}n"
    if country == "Japan":
        return "Japanese"
    if country == "Korea":
        return "Korean"
    if country == "Mexico":
        return "Mexican"
    if country == "Turkey":
        return "Turkish"
    if country == "India":
        return "Indian"
    if country == "Italy":
        return "Italian"
    if country == "France":
        return "French"
    if country == "Thailand":
        return "Thai"
    if country == "Vietnam":
        return "Vietnamese"
    return country


AREA_CENTERS = {
    "All Boston areas": BOSTON_CENTER,
    "Back Bay / South End": [42.3475, -71.0800],
    "Boston Downtown": [42.3570, -71.0585],
    "Brighton / Allston": [42.3500, -71.1360],
    "Brookline": [42.3417, -71.1212],
    "Cambridge": [42.3736, -71.1097],
    "Chinatown": [42.3502, -71.0620],
    "East Boston": [42.3751, -71.0390],
    "Fenway / Kenmore": [42.3458, -71.0988],
    "Jamaica Plain / Roxbury": [42.3126, -71.1140],
    "North End": [42.3655, -71.0542],
    "Somerville / Medford": [42.3950, -71.1050],
}


def restaurant_area(restaurant):
    """Return the nearest familiar Boston-area label for display and filtering."""
    latitude = float(restaurant.get("latitude", BOSTON_CENTER[0]))
    longitude = float(restaurant.get("longitude", BOSTON_CENTER[1]))
    candidates = {
        name: center
        for name, center in AREA_CENTERS.items()
        if name != "All Boston areas"
    }
    return min(
        candidates,
        key=lambda name: (
            (latitude - candidates[name][0]) ** 2
            + ((longitude - candidates[name][1]) * 0.75) ** 2
        ),
    )


def clean_restaurant_tags(restaurant):
    """Normalize cuisine tags while keeping location metadata out of the tag list."""
    raw_parts = re.split(r"[,;/]", restaurant.get("cuisine", ""))
    tags = []
    seen = set()
    country_tag = cuisine_label(restaurant["country"])
    for raw_part in [country_tag, *raw_parts]:
        cleaned = raw_part.strip().replace("_", " ")
        normalized = cleaned.casefold()
        if not cleaned or normalized in seen or normalized in {"boston area", "boston"}:
            continue
        seen.add(normalized)
        tags.append(cleaned.title() if cleaned.islower() else cleaned)
    return tags[:4]


def relationship_weight(relationship):
    return RELATIONSHIP_WEIGHTS.get(relationship, 1.0 if relationship == "Legacy HomeTaste check" else 0.1)


def is_lived_experience_check(review):
    return relationship_weight(review.get("relationship_to_cuisine", "Legacy HomeTaste check")) >= 0.5


def weighted_hometaste_score(reviews):
    weighted_reviews = [
        review for review in reviews
        if is_lived_experience_check(review)
    ]
    if not weighted_reviews:
        return None
    total_weight = sum(relationship_weight(review.get("relationship_to_cuisine")) for review in weighted_reviews)
    if not total_weight:
        return None
    weighted_sum = sum(
        float(review.get("rating", 0)) * relationship_weight(review.get("relationship_to_cuisine"))
        for review in weighted_reviews
    )
    return round(weighted_sum / total_weight, 2)


def nostalgia_score(score):
    """Convert the legacy 1-5 storage scale to the public 0-100 index."""
    if score is None:
        return None
    return max(0, min(100, round((float(score) - 1) * 25)))


def restaurant_checks(restaurant_name):
    return reviews_by_restaurant.get(restaurant_name, [])


def lived_experience_checks(checks):
    return [check for check in checks if is_lived_experience_check(check)]


def hometaste_summary(checks):
    lived_checks = lived_experience_checks(checks)
    score = weighted_hometaste_score(checks)
    general_count = len(checks) - len(lived_checks)
    return score, len(lived_checks), general_count


def top_signals_from_checks(checks):
    signal_labels = [
        ("ingredient_score", "ingredients"),
        ("people_language_score", "people / language"),
        ("regional_specificity_score", "regional style"),
        ("reminds_home_score", "reminds me of home"),
    ]
    scored = []
    for field_name, label in signal_labels:
        values = [
            float(check.get(field_name, 0) or 0)
            for check in checks
            if is_lived_experience_check(check) and check.get(field_name)
        ]
        if values:
            scored.append((sum(values) / len(values), label))
    scored.sort(reverse=True)
    return [label for _, label in scored[:3]]


def popup_html(restaurant, checks):
    restaurant_name = html.escape(restaurant["name"])
    score, lived_count, general_count = hometaste_summary(checks)
    cuisine_name = cuisine_label(restaurant["country"])
    if score is not None:
        score_label = f"Nostalgia Score {nostalgia_score(score)}/100"
    else:
        score_label = "Verified New - Awaiting First Local Check"

    return f"""
    <div style="font-family: Arial, sans-serif; min-width: 180px;">
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px;">{restaurant_name}</div>
        <div style="color:#075766; font-size:13px; font-weight:800; margin-top:6px;">{score_label}</div>
        <div style="color:#64748b; font-size:12px; margin-top:4px;">{html.escape(cuisine_name)} · {html.escape(restaurant_area(restaurant))}</div>
        <div style="color:#64748b; font-size:12px; margin-top:4px;">{lived_count} lived-experience checks · {general_count} general notes</div>
        <div style="color:#075766; font-size:12px; font-weight:700; margin-top:6px;">Click the marker to add a HomeTaste check.</div>
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
        return False, "HomeTaste check storage is not configured in Streamlit Secrets."

    diagnostic = review_form_diagnostic(action_url, field_map)
    if diagnostic != "configured":
        return False, diagnostic

    payload = {
        field_map["timestamp"]: review["timestamp"],
        field_map["country"]: review["country"],
        field_map["restaurant"]: review["restaurant"],
        field_map["rating"]: review["rating"],
        field_map["note"]: review.get("note", ""),
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


def value_from_structured_note(note, prefix):
    for line in str(note or "").splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "", 1).strip()
    return ""


def dimension_from_structured_note(note, label):
    marker = f"{label} "
    for part in str(note or "").replace("\n", ", ").split(","):
        cleaned = part.strip()
        if cleaned.startswith(marker):
            try:
                return str(float(cleaned.replace(marker, "", 1).strip()))
            except ValueError:
                return ""
    return ""


def public_note_text(note):
    return str(note or "").split("\n\nRelationship to cuisine:", 1)[0].strip()


def native_note_text(review):
    return (
        str(review.get("native_language_note", "") or "").strip()
        or value_from_structured_note(review.get("note", ""), "Native language voice:")
    )


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

        note = first_value(row, ["note", "notes", "comment", "explanation", "備考", "コメント"])
        relationship = (
            first_value(row, ["relationship_to_cuisine", "relationship", "relationship to cuisine"])
            or value_from_structured_note(note, "Relationship to cuisine:")
            or "Legacy HomeTaste check"
        )
        reviews.append(
            {
                "timestamp": first_value(row, ["timestamp", "time", "日時", "タイムスタンプ"]),
                "country": first_value(row, ["country", "home country", "国", "出身国"]),
                "restaurant": restaurant,
                "rating": rating_value,
                "note": note,
                "native_language_note": (
                    first_value(row, ["native_language_note", "native note", "native language voice"])
                    or value_from_structured_note(note, "Native language voice:")
                ),
                "relationship_to_cuisine": relationship,
                "ingredient_score": first_value(row, ["ingredient_score", "ingredients"]) or dimension_from_structured_note(note, "Ingredients"),
                "people_language_score": first_value(row, ["people_language_score", "people / language"]) or dimension_from_structured_note(note, "People / language"),
                "regional_specificity_score": first_value(row, ["regional_specificity_score", "regional specificity"]) or dimension_from_structured_note(note, "Regional specificity"),
                "reminds_home_score": first_value(row, ["reminds_home_score", "reminds me of home"]) or dimension_from_structured_note(note, "Reminds me of home"),
            }
        )
    return reviews


def save_review(review):
    sent_to_google_form, error_message = send_review_to_google_form(review)
    if sent_to_google_form:
        return True, ""

    fieldnames = [
        "timestamp",
        "country",
        "restaurant",
        "rating",
        "nostalgia_score",
        "note",
        "native_language_note",
        "relationship_to_cuisine",
        "weight",
        "is_lived_experience_check",
        "ingredient_score",
        "people_language_score",
        "regional_specificity_score",
        "reminds_home_score",
    ]
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
                "nostalgia_score": row.get("nostalgia_score", ""),
                "note": row.get("note", ""),
                "native_language_note": row.get("native_language_note", ""),
                "relationship_to_cuisine": row.get("relationship_to_cuisine", "Legacy HomeTaste check"),
                "weight": float(row.get("weight", 1.0) or 1.0),
                "is_lived_experience_check": row.get("is_lived_experience_check", "True") == "True",
                "ingredient_score": row.get("ingredient_score", ""),
                "people_language_score": row.get("people_language_score", ""),
                "regional_specificity_score": row.get("regional_specificity_score", ""),
                "reminds_home_score": row.get("reminds_home_score", ""),
            }
            for row in csv.DictReader(reviews_file)
            if row.get("restaurant") and row.get("rating")
        ]


def configured_google_form():
    action_url = get_setting("FEEDBACK_FORM_ACTION_URL") or get_setting("GOOGLE_FORM_ACTION_URL")
    field_map = {
        "timestamp": get_setting("FEEDBACK_FORM_TIMESTAMP_FIELD") or get_setting("GOOGLE_FORM_TIMESTAMP_FIELD"),
        "topic": get_setting("FEEDBACK_FORM_TOPIC_FIELD") or get_setting("GOOGLE_FORM_TOPIC_FIELD"),
        "country": get_setting("FEEDBACK_FORM_COUNTRY_FIELD") or get_setting("GOOGLE_FORM_COUNTRY_FIELD"),
        "restaurant": get_setting("FEEDBACK_FORM_RESTAURANT_FIELD") or get_setting("GOOGLE_FORM_RESTAURANT_FIELD"),
        "message": get_setting("FEEDBACK_FORM_MESSAGE_FIELD") or get_setting("GOOGLE_FORM_MESSAGE_FIELD"),
        "contact": get_setting("FEEDBACK_FORM_CONTACT_FIELD") or get_setting("GOOGLE_FORM_CONTACT_FIELD"),
    }
    return action_url, field_map


def send_feedback_to_google_form(feedback):
    action_url, field_map = configured_google_form()
    required_fields = ["topic", "restaurant", "message", "contact"]
    if not action_url or not all(field_map[field_name] for field_name in required_fields):
        return False

    payload = {
        field_map["topic"]: feedback["topic"],
        field_map["restaurant"]: feedback["restaurant"],
        field_map["message"]: feedback["message"],
        field_map["contact"]: feedback["contact"],
    }
    if field_map.get("timestamp"):
        payload[field_map["timestamp"]] = feedback["timestamp"]
    if field_map.get("country"):
        payload[field_map["country"]] = feedback["country"]
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
            <div class="country-button-title">Explore restaurants</div>
            <div class="country-entry-copy">Start with a cuisine, then narrow the map and list to a Boston area.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cuisine_column, area_column = st.columns(2, gap="large")
    with cuisine_column:
        country_query = st.text_input("Cuisine", placeholder="Try Japanese, Korean, Chinese...")
        country_query_normalized = country_query.strip().casefold()
        inferred_countries = [
            country
            for country in country_options
            if country_query_normalized
            and (
                country_query_normalized in country.casefold()
                or country_query_normalized in cuisine_label(country).casefold()
            )
        ]
        if not inferred_countries:
            inferred_countries = country_options

        inferred_default_index = (
            inferred_countries.index(st.session_state.get("selected_country", "Japan"))
            if st.session_state.get("selected_country", "Japan") in inferred_countries
            else 0
        )
        inferred_country = st.selectbox(
            "Selected cuisine",
            inferred_countries,
            index=inferred_default_index,
            format_func=lambda country: f"{COUNTRY_FLAGS.get(country, '')} {cuisine_label(country)}",
        )
        st.session_state.selected_country = inferred_country

    cuisine_area_options = ["All Boston areas"] + sorted({
        restaurant_area(restaurant)
        for restaurant in all_restaurants
        if restaurant["country"] == inferred_country
    })
    with area_column:
        selected_area = st.selectbox(
            "Area",
            cuisine_area_options,
            index=(
                cuisine_area_options.index(st.session_state.get("selected_area", "All Boston areas"))
                if st.session_state.get("selected_area", "All Boston areas") in cuisine_area_options
                else 0
            ),
        )
        st.session_state.selected_area = selected_area

st.markdown(
    """
    <section class="about-panel">
        <div class="about-eyebrow">Anyone can explore.</div>
        <div class="about-copy">
            HomeTaste adds lived-experience context without claiming there is only one correct version of a cuisine.
            People who know a food culture from home, family, or long-term lived experience can add checks that help everyone explore with more curiosity.
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

origin_country = st.session_state.get("selected_country", "Japan")
origin_cuisine = cuisine_label(origin_country)
origin_flag = COUNTRY_FLAGS.get(origin_country, "")
country_restaurants = [
    restaurant
    for restaurant in all_restaurants
    if restaurant["country"] == origin_country
    and (
        st.session_state.get("selected_area", "All Boston areas") == "All Boston areas"
        or restaurant_area(restaurant) == st.session_state.get("selected_area")
    )
]
visible_restaurant_names = {restaurant["name"] for restaurant in country_restaurants}
filtered_reviews = [
    review
    for review in st.session_state.reviews
    if review["country"] == origin_country
    and (
        st.session_state.get("selected_area", "All Boston areas") == "All Boston areas"
        or review["restaurant"] in visible_restaurant_names
    )
]
current_lived_reviewer_count = sum(1 for review in filtered_reviews if is_lived_experience_check(review))

st.markdown(
    f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">{html.escape(origin_cuisine)} restaurants</div>
            <div class="metric-value">{len(country_restaurants)}</div>
            <div class="metric-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 21h18"/>
                    <path d="M5 21V8l7-5 7 5v13"/>
                    <path d="M9 21v-7h6v7"/>
                </svg>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Cuisines</div>
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
            <div class="metric-label">HomeTaste checks</div>
            <div class="metric-value">{current_lived_reviewer_count}</div>
            <div class="metric-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"/>
                    <path d="M8 12.5l2.5 2.5L16 9.5"/>
                </svg>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="country-chip"><span class="flag">{origin_flag}</span><span>Showing {html.escape(origin_cuisine)} restaurants with HomeTaste checks from people who know the cuisine</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="feedback-cta">
        <div><strong>Help keep HomeTaste accurate.</strong> Missing restaurant, duplicate listing, or wrong cuisine?</div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.button("Report issue", key="feedback-cta-report", type="tertiary"):
    switch_view("Report")
    st.rerun()

selected_from_map = st.session_state.get("map_selected_restaurant") or get_query_param("selected")
selected_from_map_restaurant = next(
    (
        restaurant
        for restaurant in country_restaurants
        if restaurant["name"] == selected_from_map
    ),
    None,
)


def render_check_view():
    st.markdown(f'<div id="{RATING_FORM_ANCHOR}"></div>', unsafe_allow_html=True)
    st.subheader("Add a HomeTaste Check")
    st.markdown(
        f'<p class="section-note"><span class="flag">{origin_flag}</span> Does this place feel familiar to the {html.escape(origin_cuisine)} cuisine you know? Share what felt close to home — or what didn’t.</p>',
        unsafe_allow_html=True,
    )
    action_url, field_map = configured_review_form()
    if not action_url or not all(field_map.values()):
        st.warning("HomeTaste check storage is not fully configured. Checks will not persist after app restart until Streamlit Secrets are completed.")
    elif review_form_diagnostic(action_url, field_map) != "configured":
        st.warning(review_form_diagnostic(action_url, field_map))

    selected_restaurant = selected_from_map_restaurant
    if selected_restaurant:
        st.markdown(
            f"""
            <div class="selected-panel">
                <div class="selected-panel-title">{origin_flag} {html.escape(selected_restaurant["name"])}</div>
                <div class="selected-panel-copy">Opened from the restaurant card or map. Add your HomeTaste check below.</div>
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
        st.info("Select the matching cuisine to check the restaurant you opened from the map.")

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
        public_nostalgia_score = st.slider("Nostalgia Score", 0, 100, 75, 5)
        st.markdown('<p class="section-note">Optional context scores help future visitors understand what felt familiar.</p>', unsafe_allow_html=True)
        dimension_values = {}
        dimension_columns = st.columns(2)
        for index, (field_name, label) in enumerate(DIMENSION_FIELDS):
            with dimension_columns[index % 2]:
                dimension_values[field_name] = st.slider(label, 1.0, 5.0, 4.0, 0.5, key=f"{field_name}_slider")

        relationship_to_cuisine = st.selectbox(
            "What is your relationship to this cuisine?",
            list(RELATIONSHIP_WEIGHTS.keys()),
        )
        explanation = st.text_area(
            "What made it feel familiar or not?",
            placeholder='Example: “The small plates and casual after-work feel reminded me of places I knew in Japan, though the portions felt more American.”',
        )
        native_language_note = st.text_area(
            "Native-language voice (optional)",
            placeholder="日本語・한국어・中文などでもコメントを残せます。",
        )

        if st.button("Submit HomeTaste Check", use_container_width=True):
            cleaned_explanation = explanation.strip()
            vague_notes = {"good", "great", "authentic", "nice", "tasty", "bad", "ok", "okay"}
            if not cleaned_explanation:
                st.error("Please explain what made it feel familiar or not.")
                return
            if len(cleaned_explanation.split()) < 5 or cleaned_explanation.lower() in vague_notes:
                st.error("Please add one concrete detail: ingredient, language, clientele, regional style, portion, or service style.")
                return

            weight = relationship_weight(relationship_to_cuisine)
            is_lived_check = relationship_to_cuisine in LIVED_EXPERIENCE_RELATIONSHIPS
            structured_note = (
                f"{cleaned_explanation}\n\n"
                f"Relationship to cuisine: {relationship_to_cuisine}\n"
                f"Nostalgia Score: {public_nostalgia_score}/100\n"
                f"Native language voice: {native_language_note.strip()}\n"
                f"Context scores: "
                + ", ".join(
                    f"{label} {dimension_values[field_name]:.1f}"
                    for field_name, label in DIMENSION_FIELDS
                )
            )
            review_record = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "country": origin_country,
                "restaurant": selected_restaurant["name"],
                # Keep the legacy 1-5 storage shape so existing Google Forms remain compatible.
                "rating": 1 + (public_nostalgia_score / 25),
                "nostalgia_score": public_nostalgia_score,
                "note": structured_note,
                "native_language_note": native_language_note.strip(),
                "relationship_to_cuisine": relationship_to_cuisine,
                "weight": weight,
                "is_lived_experience_check": is_lived_check,
                **dimension_values,
            }
            st.session_state.reviews.append(review_record)
            sent_to_google_form, error_message = save_review(review_record)
            if sent_to_google_form:
                st.success(f"Thanks. Your HomeTaste check for {selected_restaurant['name']} has been added.")
            else:
                st.error("The HomeTaste check was not saved to Google Forms yet.")
                st.caption(error_message)
                st.warning("Check Streamlit Secrets and the Google Form field IDs. A local backup was saved only for this runtime.")
    else:
        st.markdown(
            """
            <div class="empty-panel">
                <div class="empty-panel-title">Choose a restaurant to check.</div>
                <div class="empty-panel-copy">Search here, or press Add a HomeTaste check from any restaurant card.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if hasattr(st, "dialog"):
    @st.dialog("Add a HomeTaste Check")
    def render_check_dialog():
        render_check_view()
        if st.button("Close check form", key="close-check-dialog"):
            st.session_state.check_dialog_open = False
            st.rerun()

else:
    def render_check_dialog():
        render_check_view()
        if st.button("Close check form", key="close-check-dialog"):
            st.session_state.check_dialog_open = False
            st.rerun()


reviews_by_restaurant = {}
for review in filtered_reviews:
    reviews_by_restaurant.setdefault(review["restaurant"], []).append(review)

average_by_restaurant = {
    restaurant_name: [review["rating"] for review in checks]
    for restaurant_name, checks in reviews_by_restaurant.items()
}

average_rows = [
    {
        "Restaurant": restaurant,
        "Nostalgia Score": nostalgia_score(weighted_hometaste_score(reviews_by_restaurant.get(restaurant, []))),
        "Lived-experience checks": len(lived_experience_checks(reviews_by_restaurant.get(restaurant, []))),
    }
    for restaurant, checks in sorted(
        reviews_by_restaurant.items(),
        key=lambda item: (
            -(weighted_hometaste_score(item[1]) or 0),
            -len(lived_experience_checks(item[1])),
            item[0],
        ),
    )
]

def restaurant_summary_row(restaurant):
    checks = restaurant_checks(restaurant["name"])
    score, lived_count, general_count = hometaste_summary(checks)
    return {
        "Restaurant": f"{origin_flag} {restaurant['name']}",
        "Nostalgia Score": nostalgia_score(score) if score is not None else "Awaiting first check",
        "Lived-experience checks": lived_count,
        "General notes": general_count,
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


def restaurant_subtype(restaurant):
    cuisine_parts = [
        part.strip().replace("_", " ")
        for part in restaurant.get("cuisine", "").split(",")
        if part.strip()
    ]
    if cuisine_parts:
        return cuisine_parts[0].title()
    return cuisine_label(restaurant["country"])


def render_restaurant_cards(restaurants, start_index=0, key_prefix="restaurant", columns_per_row=1):
    if not restaurants:
        return

    for offset, restaurant in enumerate(restaurants):
        index = start_index + offset
        checks = restaurant_checks(restaurant["name"])
        score, lived_count, general_count = hometaste_summary(checks)
        tags = clean_restaurant_tags(restaurant)
        area = restaurant_area(restaurant)
        tile_label = f"{restaurant['name']}  ·  {area}  ·  {' / '.join(tags[:3])}"
        with st.expander(tile_label):
            image_url = html.escape(restaurant.get("image_url") or restaurant_image_url(restaurant["name"]))
            public_score = nostalgia_score(score)
            score_label = (
                f"Nostalgia Score {public_score}/100"
                if public_score is not None
                else "Verified New - Awaiting First Local Check"
            )
            check_label = f"{lived_count} lived-experience check" if lived_count == 1 else f"{lived_count} lived-experience checks"
            signals = top_signals_from_checks(checks)
            signal_label = " · ".join(signals) if signals else "Cultural context is still forming."
            detail_image, detail_copy = st.columns([0.3, 0.7], gap="large")
            with detail_image:
                st.markdown(
                    f'<div class="restaurant-photo" style="background-image: url(\'{image_url}\')"></div>',
                    unsafe_allow_html=True,
                )
            with detail_copy:
                st.markdown(f"**{html.escape(cuisine_label(restaurant['country']))}** · {html.escape(area)}")
                st.markdown(" ".join(f"`{tag}`" for tag in tags))
                if public_score is None:
                    st.info(score_label)
                else:
                    st.markdown(f"### {score_label}")
                    st.caption(f"{check_label}. This reflects lived-experience checks, not general popularity.")
                st.markdown(f"**Familiarity signals:** {html.escape(signal_label)}")
                st.markdown("**Secret Menu / Authentic Customizations**")
                st.caption("Community tips coming soon, such as asking for a native-language menu or regional preparation options.")

            action_check, action_voices, action_report = st.columns([1.3, 1, 0.75])
            safe_name = re.sub(r"[^a-z0-9]+", "-", restaurant["name"].strip().lower()).strip("-")
            with action_check:
                if st.button("Add a HomeTaste check", key=f"{key_prefix}-check-{index}-{safe_name}", use_container_width=True):
                    open_check_for_restaurant(restaurant["name"])
                    st.rerun()
            with action_voices:
                if st.button("View voices", key=f"{key_prefix}-voices-{index}-{safe_name}", use_container_width=True):
                    st.session_state.voices_restaurant = restaurant["name"]
                    switch_view("Voices")
                    st.rerun()
            with action_report:
                if st.button("Report issue", key=f"{key_prefix}-report-{index}-{safe_name}", type="tertiary", use_container_width=True):
                    st.session_state.report_restaurant = restaurant["name"]
                    switch_view("Report")
                    st.rerun()


def relationship_breakdown(checks):
    breakdown = {}
    for check in checks:
        relationship = check.get("relationship_to_cuisine", "Legacy HomeTaste check")
        breakdown[relationship] = breakdown.get(relationship, 0) + 1
    return breakdown


def render_restaurant_detail(restaurant):
    checks = restaurant_checks(restaurant["name"])
    score, lived_count, general_count = hometaste_summary(checks)
    notes = [
        public_note_text(check.get("note", ""))
        for check in checks
        if public_note_text(check.get("note", ""))
    ]
    signals = top_signals_from_checks(checks)
    public_score = nostalgia_score(score)
    score_label = (
        f"Nostalgia Score {public_score}/100"
        if public_score is not None
        else "Verified New - Awaiting First Local Check"
    )
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="selected-panel">
                <div class="selected-panel-title">{origin_flag} {html.escape(restaurant["name"])}</div>
                <div class="selected-panel-copy">{html.escape(cuisine_label(restaurant["country"]))} · {html.escape(restaurant_area(restaurant))}</div>
                <div class="selected-panel-copy">{html.escape(score_label)} · {lived_count} lived-experience checks · {general_count} general diner notes</div>
                <div class="selected-panel-copy">Nostalgia Score reflects lived-experience checks, not general popularity.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if checks:
            breakdown = relationship_breakdown(checks)
            st.markdown("**Who checked it**")
            st.markdown(" · ".join(f"{count} {html.escape(label)}" for label, count in breakdown.items()))
        if signals:
            st.markdown("**Why it feels familiar**")
            st.markdown("Lived-experience checks suggest: " + " · ".join(signals))
        if notes:
            st.markdown("**Recent voices**")
            for note in notes[:3]:
                st.markdown(f'<div class="ranking-card-note">"{html.escape(note)}"</div>', unsafe_allow_html=True)
        st.markdown("**Secret Menu / Authentic Customizations**")
        st.caption("Community tips coming soon, including native-language menus and regional customization requests.")
        if st.button("Add a HomeTaste check for this place", key=f"detail-check-{restaurant['name']}", use_container_width=True):
            open_check_for_restaurant(restaurant["name"])
            st.rerun()


def ranked_restaurant_entries(restaurants):
    ranked_entries = []
    previous_score = None
    previous_rank = 0
    for position, restaurant in enumerate(restaurants, start=1):
        checks = restaurant_checks(restaurant["name"])
        score = weighted_hometaste_score(checks)
        if score is None:
            continue

        if previous_score is not None and score == previous_score:
            rank = previous_rank
        else:
            rank = position
            previous_score = score
            previous_rank = rank

        ranked_entries.append(
            {
                "rank": rank,
                "restaurant": restaurant,
                "checks": checks,
                "hometaste_score": score,
                "notes": [
                    public_note_text(review.get("note", ""))
                    for review in checks
                    if public_note_text(review.get("note", ""))
                ],
                "native_notes": [
                    native_note_text(review)
                    for review in checks
                    if native_note_text(review)
                ],
            }
        )

    return ranked_entries


def render_ranking_cards(entries, language_mode="English"):
    if not entries:
        return

    for entry in entries:
        restaurant = entry["restaurant"]
        checks = entry["checks"]
        notes = entry["native_notes"] if language_mode == "Native Language" else entry["notes"]
        lived_count = len(lived_experience_checks(checks))
        signals = top_signals_from_checks(checks)
        signal_text = " · ".join(signals) if signals else "Lived-experience voices are still forming."
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="ranking-card" style="--ranking-image: url('{restaurant_image_url(restaurant["name"])}')" title="{html.escape(notes[-1] if notes else 'No notes yet.')}">
                    <div class="ranking-badge">#{entry["rank"]} Nostalgia pick</div>
                    <div class="ranking-card-title">{origin_flag} {html.escape(restaurant["name"])}</div>
                    <div class="ranking-card-meta">Nostalgia Score {nostalgia_score(entry["hometaste_score"])}/100 · {lived_count} lived-experience checks</div>
                    <div class="signal-row">{html.escape(signal_text)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if notes:
                with st.expander(f"See voices · {language_mode}"):
                    for note in notes:
                        st.markdown(
                            f'<div class="ranking-card-note">"{html.escape(note)}"</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    f'<div class="ranking-card-empty-note">No {html.escape(language_mode.lower())} voice submitted yet.</div>',
                    unsafe_allow_html=True,
                )


sorted_country_restaurants = sorted(
    country_restaurants,
    key=lambda restaurant: (
        -(weighted_hometaste_score(restaurant_checks(restaurant["name"])) or 0),
        -len(lived_experience_checks(restaurant_checks(restaurant["name"]))),
        -len([review for review in restaurant_checks(restaurant["name"]) if review.get("note", "").strip()]),
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
        restaurant_map.get_root().html.add_child(
            folium.Element(
                """
                <style>
                .leaflet-control-attribution {
                    font-size: 9px !important;
                    opacity: 0.58 !important;
                    transform: scale(0.78);
                    transform-origin: bottom right;
                }
                </style>
                """
            )
        )
        for restaurant in country_restaurants:
            checks = restaurant_checks(restaurant["name"])
            score, lived_count, _ = hometaste_summary(checks)
            tooltip_label = (
                f"{html.escape(restaurant['name'])} · Nostalgia Score {nostalgia_score(score)}/100 · {lived_count} checks"
                if score is not None
                else f"{html.escape(restaurant['name'])} · Verified New - Awaiting First Local Check"
            )
            folium.CircleMarker(
                location=[restaurant["latitude"], restaurant["longitude"]],
                radius=7,
                color="#075766",
                fill=True,
                fill_color="#0f7f8c",
                fill_opacity=0.9,
                popup=folium.Popup(popup_html(restaurant, checks), max_width=260),
                tooltip=tooltip_label,
            ).add_to(restaurant_map)

        map_data = st_folium(restaurant_map, width=640, height=520)
        clicked_restaurant = restaurant_from_map_click(
            country_restaurants,
            map_data.get("last_object_clicked") if map_data else None,
        )
        if clicked_restaurant and st.session_state.get("map_selected_restaurant") != clicked_restaurant["name"]:
            open_check_for_restaurant(clicked_restaurant["name"])
            st.rerun()

    with list_area:
        selected_map_name = st.session_state.get("map_selected_restaurant")
        if selected_map_name:
            selected_detail = next(
                (restaurant for restaurant in country_restaurants if restaurant["name"] == selected_map_name),
                None,
            )
            if selected_detail:
                render_restaurant_detail(selected_detail)

        top_rated_rows = [
            restaurant
            for restaurant in sorted_country_restaurants
            if weighted_hometaste_score(restaurant_checks(restaurant["name"])) is not None
        ][:5]
        st.subheader("Recommended by people who know this cuisine")
        if top_rated_rows:
            render_restaurant_cards(top_rated_rows[:3], key_prefix="popular", columns_per_row=1)
        else:
            st.markdown(
                """
                <div class="empty-panel">
                    <div class="empty-panel-title">No HomeTaste checks yet.</div>
                    <div class="empty-panel-copy">A few high-priority places are shown below so people with lived experience can add the first cultural context.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_restaurant_cards(sorted_country_restaurants[:3], key_prefix="popular-empty", columns_per_row=1)


    st.markdown('<div id="restaurants-section"></div>', unsafe_allow_html=True)
    st.subheader(f"{origin_cuisine} Restaurants")
    st.markdown(
        f'<p class="section-note">{len(country_restaurants)} places found. Restaurants with stronger lived-experience HomeTaste checks appear first. Places with no checks are shown lower until more people add context.</p>',
        unsafe_allow_html=True,
    )
    render_restaurant_cards(sorted_country_restaurants[:12], key_prefix="list")
    if len(sorted_country_restaurants) > 12:
        with st.expander("Show more restaurants"):
            render_restaurant_cards(sorted_country_restaurants[12:48], start_index=12, key_prefix="more")


def render_voices_view():
    st.markdown('<div id="reviews-section"></div>', unsafe_allow_html=True)
    st.subheader("Voices")
    st.markdown(
        f'<p class="section-note">See which {origin_flag} {html.escape(origin_cuisine)} restaurants feel familiar to people with lived experience of this cuisine.</p>',
        unsafe_allow_html=True,
    )
    language_mode = st.radio(
        "Voice language",
        ["English", "Native Language"],
        horizontal=True,
        key="voice-language-mode",
    )

    if average_rows:
        st.subheader("Most familiar right now")
        ranked_restaurants = [
            restaurant
            for restaurant in sorted_country_restaurants
            if weighted_hometaste_score(restaurant_checks(restaurant["name"])) is not None
        ]
        selected_voice_restaurant = st.session_state.get("voices_restaurant")
        if selected_voice_restaurant:
            ranked_restaurants = sorted(
                ranked_restaurants,
                key=lambda restaurant: restaurant["name"] != selected_voice_restaurant,
            )
            st.caption(f"Showing {selected_voice_restaurant} first, followed by the cuisine ranking.")
        ranked_entries = ranked_restaurant_entries(ranked_restaurants)
        render_ranking_cards(ranked_entries[:5], language_mode=language_mode)
        if len(ranked_entries) > 5:
            with st.expander("Show more"):
                render_ranking_cards(ranked_entries[5:], language_mode=language_mode)
    else:
        st.markdown(
            """
            <div class="empty-panel">
                <div class="empty-panel-title">No HomeTaste checks yet.</div>
                <div class="empty-panel-copy">Use Explore or Add a Check to add the first lived-experience context.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if get_setting("REVIEW_SHEET_CSV_URL"):
            st.caption("If your Google Sheet already has responses, make sure the response Sheet is shared or published so the app can read its CSV URL.")


def render_report_view():
    st.markdown('<div id="feedback-section"></div>', unsafe_allow_html=True)
    st.subheader("Report issue")
    st.markdown(
        '<p class="section-note">Help keep HomeTaste accurate. Found a duplicate, wrong cuisine, missing restaurant, or map issue? Send it to the team.</p>',
        unsafe_allow_html=True,
    )
    with st.form("feedback_form"):
        feedback_topic = st.selectbox(
            "Issue type",
            [
                "wrong cuisine",
                "duplicate restaurant",
                "closed restaurant",
                "wrong location",
                "wrong image",
                "offensive/inappropriate content",
                "Other",
            ],
        )
        feedback_restaurant = st.text_input(
            "Restaurant name optional",
            value=st.session_state.get("report_restaurant", ""),
        )
        feedback_message = st.text_area("Description")
        feedback_contact = st.text_input("Email optional")
        feedback_submitted = st.form_submit_button("Report issue")

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
                    st.success("Thanks. Your report has been sent to the team.")
                else:
                    st.success("Thanks. Your report has been saved for the team.")
                    st.caption("Google Form delivery is not configured yet, so this prototype kept a local backup.")
            else:
                st.error("Please describe what should be fixed.")


if st.session_state.get("check_dialog_open"):
    render_check_dialog()


if st.session_state.active_view == "Check":
    render_check_view()
elif st.session_state.active_view == "Voices":
    render_voices_view()
elif st.session_state.active_view == "Report":
    render_report_view()
else:
    render_explore_view()
