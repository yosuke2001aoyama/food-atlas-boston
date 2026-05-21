# Food Atlas Boston

Streamlit app for discovering Boston restaurants by home cuisine and collecting authenticity ratings.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Local URL:

```text
http://localhost:8501/
```

## Deploy publicly

1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, `.gitignore`, and this `README.md`.
3. Deploy the repository with Streamlit Community Cloud or another Streamlit host.
4. Add Streamlit secrets for Google Form review storage.
5. Set environment variables or Streamlit secrets for Google Form delivery if feedback should go directly to operators.

## Google Form feedback integration

Create a Google Form with fields for topic, country, restaurant, message, and contact.
Then configure these values in the deployed app environment:

```text
GOOGLE_FORM_ACTION_URL=https://docs.google.com/forms/d/e/.../formResponse
GOOGLE_FORM_TOPIC_FIELD=entry.xxxxx
GOOGLE_FORM_COUNTRY_FIELD=entry.xxxxx
GOOGLE_FORM_RESTAURANT_FIELD=entry.xxxxx
GOOGLE_FORM_MESSAGE_FIELD=entry.xxxxx
GOOGLE_FORM_CONTACT_FIELD=entry.xxxxx
```

The app also keeps a local backup in `feedback.csv` when running locally.

## Ratings storage

Public reviews are submitted through a Google Form and read back from the linked Google Sheet's published CSV URL. This avoids service account keys, which many Google Cloud projects block by default.

Create a Google Form with these fields:

```text
timestamp
country
restaurant
rating
note
```

Link the form to a Google Sheet. In the response Sheet, rename the columns to:

```text
timestamp,country,restaurant,rating,note
```

Then publish that response Sheet as CSV and add these values in **Streamlit Community Cloud → App settings → Secrets**:

```toml
REVIEW_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
REVIEW_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/.../formResponse"
REVIEW_FORM_TIMESTAMP_FIELD = "entry.xxxxx"
REVIEW_FORM_COUNTRY_FIELD = "entry.xxxxx"
REVIEW_FORM_RESTAURANT_FIELD = "entry.xxxxx"
REVIEW_FORM_RATING_FIELD = "entry.xxxxx"
REVIEW_FORM_NOTE_FIELD = "entry.xxxxx"
```

The app falls back to `reviews.csv` only for local testing.
