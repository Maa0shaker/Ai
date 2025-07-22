import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText

SCOPE = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")


def get_sheet():
    creds_path = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_path or not SHEET_ID:
        st.error("لم يتم ضبط إعدادات جوجل")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1


def load_data(sheet):
    values = sheet.get_all_records()
    if values:
        df = pd.DataFrame(values)
    else:
        df = pd.DataFrame(columns=["ApartmentID", "Address", "Rent", "TenantName", "Email", "StartDate", "Months", "LastAlert"])
    return df


def save_data(df, sheet):
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())


def send_email(to_email, subject, body):
    host = os.getenv("SMTP_SERVER")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    port = int(os.getenv("SMTP_PORT", "587"))
    if not host or not user or not password:
        st.warning("إعدادات البريد غير مكتملة")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def main():
    st.title("تطبيق إدارة تأجير الشقق")
    sheet = get_sheet()
    df = load_data(sheet)

    menu = st.sidebar.selectbox("القائمة", ["إضافة شقة", "عرض الشقق", "تنبيهات الإيجار"])

    if menu == "إضافة شقة":
        with st.form("add_form"):
            aid = st.text_input("رقم الشقة")
            address = st.text_input("العنوان")
            rent = st.number_input("الإيجار الشهري", step=1)
            submitted = st.form_submit_button("إضافة")
        if submitted and aid:
            df.loc[len(df)] = [aid, address, rent, "", "", "", "", ""]
            save_data(df, sheet)
            st.success("تمت الإضافة")

    elif menu == "عرض الشقق":
        st.dataframe(df)
        if not df.empty:
            with st.form("book_form"):
                apt = st.selectbox("اختر الشقة", df["ApartmentID"])
                tenant = st.text_input("اسم المستأجر")
                email = st.text_input("البريد الإلكتروني")
                start_date = st.date_input("تاريخ البدء")
                months = st.number_input("مدة العقد بالأشهر", step=1)
                submitted = st.form_submit_button("حجز")
            if submitted:
                idx = df.index[df["ApartmentID"] == apt][0]
                df.loc[idx, ["TenantName", "Email", "StartDate", "Months"]] = [tenant, email, start_date.strftime("%Y-%m-%d"), months]
                save_data(df, sheet)
                st.success("تم الحجز")

    else:
        today = datetime.today()
        alerts = []
        for idx, row in df.iterrows():
            if row.get("TenantName") and row.get("StartDate") and row.get("Months"):
                start = datetime.strptime(row["StartDate"], "%Y-%m-%d")
                due = start + timedelta(days=30*int(row["Months"]))
                if due - today <= timedelta(days=30):
                    if not row.get("LastAlert"):
                        send_email(row["Email"], "تنبيه انتهاء عقد الإيجار", f"تنتهي مدة عقد الشقة {row['ApartmentID']} في {due.date()}")
                        df.loc[idx, "LastAlert"] = today.strftime("%Y-%m-%d")
                        alerts.append(row["ApartmentID"])
        if alerts:
            save_data(df, sheet)
            st.write("تم إرسال التنبيهات للشقق:", alerts)
        else:
            st.write("لا يوجد تنبيهات حالياً")


if __name__ == "__main__":
    main()
