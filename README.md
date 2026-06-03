# HomeTaste Boston

HomeTaste Boston is a Streamlit app for discovering Boston restaurants through lived-experience food knowledge.

Most restaurant apps show what is popular. HomeTaste adds a different layer: what feels familiar, comforting, and culturally true to people who grew up with, lived with, or deeply know a cuisine.

This is not a generic restaurant review site, and it is not meant to gatekeep food. Anyone can explore. People with lived experience can add HomeTaste checks that give other diners more context.

## Core Features

- Choose a cuisine you know from lived experience.
- Explore Boston restaurants on a map.
- See HomeTaste Scores from lived-experience checks.
- Add structured HomeTaste checks with relationship-to-cuisine context.
- Browse voices and explanations from people who know the cuisine.
- Report incorrect restaurant data, duplicates, location issues, or image issues.

## Philosophy

HomeTaste is not about saying who is allowed to enjoy a cuisine.

It is about adding context.

Anyone can use mainstream restaurant apps to see what is popular. HomeTaste helps you see what feels familiar to people who grew up with, lived with, or deeply know a cuisine, so you can explore Boston restaurants with more curiosity, respect, and better recommendations.

We do not believe food has only one correct version. Diaspora food changes, adapts, and becomes local. HomeTaste is not here to police authenticity. It simply adds a missing layer to restaurant discovery: lived-experience perspective.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Local URL:

```text
http://localhost:8501/
```

## Deploy Publicly

1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, `.gitignore`, `.streamlit/config.toml`, and this `README.md`.
3. Deploy the repository with Streamlit Community Cloud or another Streamlit host.
4. Add Streamlit secrets for Google Form check storage.
5. Add Streamlit secrets for issue reports if reports should go directly to operators.

## Public Hosting And Sleep Screens

Streamlit Community Cloud can put inactive apps to sleep. When that happens, visitors may see a wake-up or "ZZZ" screen before the app loads again. That behavior is controlled by the hosting service, not by `app.py`, so it cannot be reliably removed from inside the app code.

For a consumer-facing public launch, use an always-on hosting option such as a paid Streamlit plan or another always-on host. Avoid relying on keep-alive pings as a production fix because they are fragile and may conflict with a host's usage policy.

## HomeTaste Check Storage

Public HomeTaste checks are submitted through a Google Form and read back from the linked Google Sheet's published CSV URL. This avoids service account keys, which many Google Cloud projects block by default.

The current app remains compatible with the existing Google Form fields:

```text
timestamp
country
restaurant
rating
note
```

The app stores newer HomeTaste details inside the note field as structured text, so the current form can continue working without a database migration.

Add these values in **Streamlit Community Cloud -> App settings -> Secrets**:

```toml
REVIEW_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1CwuBzDyTWOXvWgARrSqAxMH70xoxYaG-iWkYmOLRo5I/export?format=csv&gid=349385528"
REVIEW_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/1FAIpQLSezjgoihhcW_OZLbt5ictQ8B9p7gepciIOdv0YMVPU1o2gxrg/formResponse"
REVIEW_FORM_TIMESTAMP_FIELD = "entry.1083137322"
REVIEW_FORM_COUNTRY_FIELD = "entry.284631955"
REVIEW_FORM_RESTAURANT_FIELD = "entry.1872716998"
REVIEW_FORM_RATING_FIELD = "entry.49189999"
REVIEW_FORM_NOTE_FIELD = "entry.942014209"
```

## Report Issue Storage

Issue reports are separate from HomeTaste checks. The clean setup is:

1. Create or use a second Google Form for operator reports.
2. Link that form to a response sheet.
3. Add these values in Streamlit Secrets.

```toml
FEEDBACK_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfBaDjHXkAsVflYjAsfQ0PqesjUyoB5xa_I1G5v_RKrgJV3rA/formResponse"
FEEDBACK_FORM_TIMESTAMP_FIELD = "entry.1002726540"
FEEDBACK_FORM_TOPIC_FIELD = "entry.1301236709"
FEEDBACK_FORM_RESTAURANT_FIELD = "entry.744111579"
FEEDBACK_FORM_MESSAGE_FIELD = "entry.1754693192"
FEEDBACK_FORM_CONTACT_FIELD = "entry.734363110"
```

The app also keeps a local backup in `feedback.csv` when running locally.

## Future Work

- Better duplicate handling and canonical restaurant IDs.
- Real restaurant photo pipeline.
- Cuisine region and subtype classification.
- Dedicated weighted scoring fields in the Google Form or a database.
- Moderation and quality checks for vague submissions.
- Multi-city expansion beyond Boston.
