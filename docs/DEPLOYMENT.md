# 🚀 Deployment Guide: BACB Fieldwork Tracker

This guide walks you through deploying your tracker to the **Streamlit Community Cloud** (free) so you can access it from any device.

## 1. Prerequisites
* **GitHub Account**: Your code must be in a GitHub repository (it is).
* **Streamlit Account**: Sign up at [share.streamlit.io](https://share.streamlit.io) using your GitHub account.
* **Google Cloud Service Account**: You should have your `service_account.json` and your Google Sheet ready (from Unit 1).

## 2. Prepare Your Secrets
The Streamlit Cloud needs your secrets (password and Google credentials) effectively "injected" into it, since we don't commit `secrets.toml` to GitHub.

1. Open your local `.streamlit/secrets.toml` file.
2. Copy the **entire content**. It should look something like this:

```toml
APP_PASSWORD = "your-password-here"

[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/..."
type = "streamlit_gsheets.GSheetsConnection"
service_account = { "type": "service_account", "project_id": "...", ... }
```

> **Note:** If your `secrets.toml` uses a file path for `service_account` (e.g., `service_account = "service_account.json"`), you **MUST** convert it to the dictionary format shown above for the Cloud.
>
> **How to convert:**
> Copy the *content* of `service_account.json` and paste it as the value for `service_account` in the TOML, surrounding it with `{...}` if needed, or simply pasting the JSON object. 
> *Ideally, your `secrets.toml` currently looks like the example above.*

## 3. Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Click **"New app"**.
3. Select your repository (`bcba-tracker`), branch (`main`), and main file (`app.py`).
4. **BEFORE** clicking "Deploy", click **"Advanced settings..."**.
5. Paste your copied secrets into the "Secrets" text area.
6. Click **"Save"**.
7. Click **"Deploy"**.

## 4. Verify
1. Wait for the app to build (takes 1-2 minutes).
2. Once live, enter your password.
3. Try adding a Supervisor in "Settings" to verify the database connection.
4. Try logging a test session.

## 5. Troubleshooting
* **"FileNotFoundError"**: Ensure you didn't commit a path to a missing JSON file. Use the dictionary format for secrets.
* **"Authentication Error"**: Verify the Service Account email (in secrets) is shared as "Editor" on your Google Sheet.
