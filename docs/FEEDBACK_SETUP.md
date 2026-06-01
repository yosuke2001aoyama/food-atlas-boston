# Report Issue Setup

Issue reports should use a separate Google Form from HomeTaste checks.

Why:

- HomeTaste check fields are timestamp, cuisine/country, restaurant, score, and structured note.
- Report issue fields are issue type, restaurant, message, and contact. Cuisine/country is optional.
- Keeping them separate prevents operator reports from mixing with public HomeTaste checks.

Recommended setup:

1. Open the same Google Sheet used for HomeTaste check responses.
2. Create a new Google Form for issue reports.
3. Add these fields:
   - issue type
   - restaurant
   - message
   - contact
4. Optionally add cuisine/country if operators need it.
5. In the report Form, link responses to the same Google Sheet.
6. Google will create a separate response tab for reports.
7. Get the report Form action URL and entry IDs.
8. Paste them into Streamlit Secrets using `.streamlit/secrets.toml.example`.

Current report Form mapping:

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
- If the form does not include a cuisine/country question, leave `FEEDBACK_FORM_COUNTRY_FIELD` unset.

The app will then send Report issue page submissions directly to that Form.

If report secrets are not configured, the app falls back to `feedback.csv` only when running locally. That local file is not reliable for a public multi-user app.
