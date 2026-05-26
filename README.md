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
5. Set Streamlit secrets for feedback delivery if feedback should go directly to operators.

## Feedback storage

Feedback is separate from ratings. The clean setup is:

1. Create a second Google Form for operator feedback.
2. Link that form to the same Google Sheet as the rating form.
3. Google will create a separate response tab, so reviews and feedback stay separated.
4. Add these values in **Streamlit Community Cloud → App settings → Secrets**.

Create a feedback Google Form with these fields:

```text
timestamp
Issue type
Restaurant name optional
What should we fix?
Email optional
```

Then configure these values. `FEEDBACK_FORM_COUNTRY_FIELD` is optional; only use it if the feedback form also has a country question.

```toml
FEEDBACK_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/.../formResponse"
FEEDBACK_FORM_TOPIC_FIELD = "entry.xxxxx"
FEEDBACK_FORM_RESTAURANT_FIELD = "entry.xxxxx"
FEEDBACK_FORM_MESSAGE_FIELD = "entry.xxxxx"
FEEDBACK_FORM_CONTACT_FIELD = "entry.xxxxx"
# Optional:
# FEEDBACK_FORM_COUNTRY_FIELD = "entry.xxxxx"
```

Older `GOOGLE_FORM_*` feedback secret names still work, but `FEEDBACK_FORM_*` is clearer.
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

Then publish that response Sheet as CSV and add these values in **Streamlit Community Cloud → App settings → Secrets**. Make sure the `gid` belongs to the Google Form response tab, not an empty first sheet.

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

If reviews do not appear in the Google Form response Sheet, open the app's Rate page and submit a test review. The app will show whether the Google Form submission succeeded or which secret is missing.
