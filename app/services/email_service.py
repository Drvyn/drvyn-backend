# email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.sender_email = os.getenv("SMTP_EMAIL")
        self.sender_password = os.getenv("SMTP_PASSWORD")
        
    async def send_booking_notification(self, booking_data, admin_emails):
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(admin_emails)
            msg['Subject'] = f"New Booking: {booking_data['brand']} {booking_data['model']}"
            
            # Create email body
            body = f"""
            New Booking Received:
            
            Customer Details:
            - Phone: {booking_data.get('phone', 'N/A')}
            - Alternate Phone: {booking_data.get('alternatePhone', 'N/A')}
            - Address: {booking_data.get('address', 'N/A')}
            
            Vehicle Details:
            - Brand: {booking_data.get('brand', 'N/A')}
            - Model: {booking_data.get('model', 'N/A')}
            - Fuel Type: {booking_data.get('fuelType', 'N/A')}
            - Year: {booking_data.get('year', 'N/A')}
            
            Service Details:
            - Date: {booking_data.get('date', 'N/A')}
            - Time: {booking_data.get('time', 'N/A')}
            - Service Center: {booking_data.get('serviceCenter', 'N/A')}
            - Total Price: ₹{booking_data.get('totalPrice', 0)}
            
            Services Requested:
            {chr(10).join([f"  • {item['packageName']} (Qty: {item['quantity']}, ₹{item['price']})" for item in booking_data.get('cartItems', [])])}
            
            Booking Time: {booking_data.get('createdAt', 'N/A')}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            logger.info("Booking notification email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

# Initialize email service
email_service = EmailService()