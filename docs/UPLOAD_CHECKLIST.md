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
5. Replace the report placeholders after creating the report issue Google Form.
6. Save changes and reboot the app.

Public app data flow:

- HomeTaste checks go to the check Google Form and are read back from the linked Google Sheet CSV.
- Issue reports go to the report Google Form and appear in a separate tab of the same Google Sheet.
