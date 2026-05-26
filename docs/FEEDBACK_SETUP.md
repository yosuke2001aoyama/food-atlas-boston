# Feedback Setup

Feedback should use a separate Google Form from ratings.

Why:

- Rating fields are timestamp, country, restaurant, rating, and note.
- Feedback fields are issue type, restaurant, message, and contact. Country is optional.
- Keeping them separate prevents operator feedback from mixing with public ratings.

Recommended setup:

1. Open the same Google Sheet used for rating responses.
2. Create a new Google Form for feedback.
3. Add these fields:
   - issue type
   - restaurant
   - message
   - contact
4. Optionally add country if operators need it in feedback.
5. In the feedback Form, link responses to the same Google Sheet.
6. Google will create a separate response tab for feedback.
7. Get the feedback Form action URL and entry IDs.
8. Paste them into Streamlit Secrets using `.streamlit/secrets.toml.example`.

Current feedback Form mapping:

```toml
FEEDBACK_FORM_ACTION_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfBaDjHXkAsVflYjAsfQ0PqesjUyoB5xa_I1G5v_RKrgJV3rA/formResponse"
FEEDBACK_FORM_TIMESTAMP_FIELD = "entry.1002726540"
FEEDBACK_FORM_TOPIC_FIELD = "entry.1301236709"
FEEDBACK_FORM_RESTAURANT_FIELD = "entry.744111579"
FEEDBACK_FORM_MESSAGE_FIELD = "entry.1754693192"
FEEDBACK_FORM_CONTACT_FIELD = "entry.734363110"
```

Important:

- Creating a new sheet tab alone is not enough. The app submits to a Google Form endpoint, and Google Forms writes to the linked Sheet.
- If the form does not include a country question, leave `FEEDBACK_FORM_COUNTRY_FIELD` unset.

The app will then send Feedback page submissions directly to that feedback Form.

If feedback secrets are not configured, the app falls back to `feedback.csv` only when running locally. That local file is not reliable for a public multi-user app.
