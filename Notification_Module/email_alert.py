import smtplib
from email.message import EmailMessage
from utils.location import get_live_location   # ✅ import from location.py

# 🔐 Your Gmail credentials (⚠️ keep safe)
SENDER_EMAIL = "bibhudattabehera10@gmail.com"
APP_PASSWORD = "lxtnnmfkbkkslckl"

def send_email_alert(receiver, event_type):
    try:
        # 📍 Get real-time location
        lat, lon, location_link = get_live_location()

        # 📧 Create email
        msg = EmailMessage()
        msg.set_content(
            f"""
⚠️ ANOMALY ALERT ⚠️

Event Type : {event_type}

📍 Coordinates:
Latitude  : {lat}
Longitude : {lon}

📍 Live Location:
{location_link}

Please take immediate action.
"""
        )

        msg["Subject"] = f"{event_type} Alert Notification"
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver

        # 🔌 Connect & send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        print("✅ Email sent successfully with location!")

    except Exception as e:
        print("❌ Error sending email:", e)


# 🚀 TEST (optional)
if __name__ == "__main__":
    send_email_alert("itsmebvu@gmail.com", "Fall Detected")