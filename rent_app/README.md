# Streamlit Apartment Rental App

This simple Streamlit application provides an Arabic interface for managing apartment rentals. Data is stored in a Google Sheet.

## Setup
1. Create a Google service account and share your sheet with it.
2. Set environment variables:
   - `GOOGLE_CREDENTIALS`: path to the service account JSON file.
   - `GOOGLE_SHEET_ID`: the ID of the spreadsheet.
   - For email reminders: `SMTP_SERVER`, `SMTP_USER`, `SMTP_PASSWORD`, and optional `SMTP_PORT`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run streamlit_app.py
   ```
