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
4. Set environment variables or Streamlit secrets for Google Form delivery if feedback should go directly to operators.

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

The current prototype stores ratings in `reviews.csv`. This is fine for local testing, but a public multi-user version should use a shared backend such as Google Sheets, Supabase, Airtable, or a small API.
