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
4. Add Streamlit secrets for Google Sheets review storage.
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

Public reviews are stored in Google Sheets when `GOOGLE_SHEET_ID` and a Google service account are configured in Streamlit secrets. The app falls back to `reviews.csv` only for local testing.

Create a Google Sheet with a tab named `reviews`, then add this header row:

```text
timestamp,country,restaurant,rating,note
```

In Streamlit Community Cloud, open **App settings → Secrets** and add:

```toml
GOOGLE_SHEET_ID = "your_google_sheet_id"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Share the Google Sheet with the service account `client_email` as an editor.
