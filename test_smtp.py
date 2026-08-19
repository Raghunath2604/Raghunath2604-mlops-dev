import smtplib
import socket

try:
    print("Testing port 465...")
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5)
    print("Port 465 Connected!")
    server.quit()
except Exception as e:
    print("Port 465 Failed:", e)

try:
    print("Testing port 587...")
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)
    server.starttls()
    print("Port 587 Connected!")
    server.quit()
except Exception as e:
    print("Port 587 Failed:", e)
