import os
import sys
import smtplib
import time

from dotenv import load_dotenv
load_dotenv()

# import imghdr > this package is outdated as of 2025
# ^^^^^^^^^^^^^ is needed to attach images to mails

from email.message import EmailMessage

SENDER_EMAIL_ADDRESS = os.getenv('EMAIL_USER')
SENDER_EMAIL_PASSWORD = os.getenv('EMAIL_PASS')

def send_email(recepient_email, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL_ADDRESS
    msg['To'] = recepient_email
    msg.set_content(body)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL_ADDRESS, SENDER_EMAIL_PASSWORD)
        smtp.send_message(msg)
        

def main():
    print("Welcome!")
    resp = int(input("""
                     Choose your option: 
                     1 == Many recepients
                     2 == Many emails
    : """))
    if resp == 1:
        recepient_list = []
        while True:
            recepient = input("Enter the recepient email: ")
            if recepient.lower == "q":
                break
            recepient_list.append(recepient)
        subject = input("Enter the subject: ")
        print("Enter the message body, Press CTRL+D (Linux/Mac) or CTRL+Z (Windows) to finish:")
        body = sys.stdin.read()
        print("Body:\n", body)
        for rece in recepient_list:
            send_email(rece, subject=subject, body=body)
            time.sleep(1)
    elif resp == 2:
        n = int(input("Enter the count: "))
        recepient = input("Enter the recepient email: ")
        subject = input("Enter the subject: ")
        print("Enter the message body, Press CTRL+D (Linux/Mac) or CTRL+Z (Windows) to finish:")
        body = sys.stdin.read()
        print("Body:\n", body)
        for i in range(n):
            send_email(recepient,subject,body)
            time.sleep(1)

if __name__ == "__main__":
    main()