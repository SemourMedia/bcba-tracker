# 🔐 Google Sheets Setup Guide

The **BACB Fieldwork Tracker** follows a "Bring Your Own Data" philosophy. You own the database (the Google Sheet). For the app to write data to your sheet, you must share it with the app's Service Account.

## Prerequisite
You should have a `service_account.json` file from the initial setup steps.

## Step 1: Find the Service Account Email
1. Open your `service_account.json` file in a text editor.
2. Look for the `"client_email"` field.
3. It should look something like: `bcba-tracker-bot@project-id.iam.gserviceaccount.com`
4. **Copy this email address.**

## Step 2: Prepare Your Sheet
1. Create a new Google Sheet (or use an existing one).
2. Rename the first tab to `Logs` (Case sensitive).
3. Create a second tab and name it `Config`.

## Step 3: Share the Sheet
1. In your Google Sheet, click the big green **Share** button in the top right.
2. Paste the **Service Account Email** you copied in Step 1.
3. Ensure the permission is set to **Editor**.
4. Uncheck "Notify people" (optional, since it's a bot).
5. Click **Share**.

## Step 4: Verification
The app will now be able to read and write to this sheet once the secrets are configured in the application.
