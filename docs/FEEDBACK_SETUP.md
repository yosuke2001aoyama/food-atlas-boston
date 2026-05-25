# Feedback Setup

Feedback should use a separate Google Form from ratings.

Why:

- Rating fields are timestamp, country, restaurant, rating, and note.
- Feedback fields are issue type, country, restaurant, message, and contact.
- Keeping them separate prevents operator feedback from mixing with public ratings.

Recommended setup:

1. Open the same Google Sheet used for rating responses.
2. Create a new Google Form for feedback.
3. Add these fields:
   - issue type
   - country
   - restaurant
   - message
   - contact
4. In the feedback Form, link responses to the same Google Sheet.
5. Google will create a separate response tab for feedback.
6. Get the feedback Form action URL and entry IDs.
7. Paste them into Streamlit Secrets using `.streamlit/secrets.toml.example`.

The app will then send Feedback page submissions directly to that feedback Form.

If feedback secrets are not configured, the app falls back to `feedback.csv` only when running locally. That local file is not reliable for a public multi-user app.
