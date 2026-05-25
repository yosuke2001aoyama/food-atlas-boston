# Upload Checklist

Upload these files and folders to GitHub:

```text
app.py
requirements.txt
README.md
.gitignore
.streamlit/config.toml
docs/FEEDBACK_SETUP.md
docs/UPLOAD_CHECKLIST.md
```

Do not upload a real `.streamlit/secrets.toml` file.

Use `.streamlit/secrets.toml.example` only as a copy-paste template for Streamlit Community Cloud:

1. Open Streamlit Community Cloud.
2. Open the app settings.
3. Open Secrets.
4. Paste the template contents.
5. Replace the feedback placeholders after creating the feedback Google Form.
6. Save changes and reboot the app.

Public app data flow:

- Ratings go to the rating Google Form and are read back from the linked Google Sheet CSV.
- Feedback goes to the feedback Google Form and appears in a separate tab of the same Google Sheet.
