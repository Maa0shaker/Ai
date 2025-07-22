import os
import smtplib
import schedule
import time
from datetime import datetime, timedelta
from typing import Optional

import openai
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
APARTMENT_SHEET_NAME = "Apartments"
BOOKING_SHEET_NAME = "Bookings"

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Google Sheets setup
credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_file:
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID)
    apartment_sheet = sheet.worksheet(APARTMENT_SHEET_NAME)
    booking_sheet = sheet.worksheet(BOOKING_SHEET_NAME)
else:
    apartment_sheet = booking_sheet = None

class Apartment(BaseModel):
    name: str
    address: str
    price: float

class Booking(BaseModel):
    apartment_name: str
    renter_email: str
    start_date: datetime
    end_date: datetime

@app.post("/apartments")
def add_apartment(apartment: Apartment):
    if apartment_sheet:
        apartment_sheet.append_row([apartment.name, apartment.address, apartment.price])
    return {"status": "ok"}

@app.post("/bookings")
def add_booking(booking: Booking):
    if booking_sheet:
        booking_sheet.append_row([
            booking.apartment_name,
            booking.renter_email,
            booking.start_date.strftime("%Y-%m-%d"),
            booking.end_date.strftime("%Y-%m-%d"),
        ])
    return {"status": "ok"}

def send_email(to_address: str, subject: str, body: str):
    if not (EMAIL_HOST and EMAIL_USER and EMAIL_PASS):
        print("Email credentials not configured")
        return
    message = f"From: {EMAIL_USER}\nTo: {to_address}\nSubject: {subject}\n\n{body}"
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [to_address], message)

def generate_email_body(apartment_name: str, end_date: datetime) -> str:
    prompt = (
        f"Compose a friendly reminder email about an upcoming rent payment for the "
        f"apartment '{apartment_name}' due on {end_date.strftime('%Y-%m-%d')}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Rent is due on {end_date.strftime('%Y-%m-%d')}."

def check_payments():
    if not booking_sheet:
        return
    today = datetime.utcnow().date()
    upcoming = today + timedelta(days=30)
    records = booking_sheet.get_all_records()
    for rec in records:
        end_date = datetime.strptime(rec["end_date"], "%Y-%m-%d").date()
        if today <= end_date <= upcoming:
            email_body = generate_email_body(rec["apartment_name"], end_date)
            send_email(rec["renter_email"], "Upcoming Rent Payment", email_body)

schedule.every().day.at("09:00").do(check_payments)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)
