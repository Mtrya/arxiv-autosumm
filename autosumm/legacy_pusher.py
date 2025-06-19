from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config import *
import traceback
import os


class Pusher:
    def __init__(self):
        # Datetime
        now = datetime.now()
        iso_calender = now.isocalendar()
        current_year = iso_calender.year
        current_week_number = iso_calender.week
        self.category = CATEGORIES[now.weekday()]
        self.path = (
            f"/mnt/data/summaries/{current_year}/"
            f"{self.category.replace('.', '')}/"
            f"summary_{self.category.replace('.', '')}_"
            f"{current_year-2000:02d}{current_week_number:02d}"
        )
        #print(self.path)

    def push_to_email(self):
        msg = MIMEMultipart()
        msg["From"] = MAIL_USER
        msg["To"] = MAIL_RECEIVER
        msg["Subject"] = f"ArXiv Summary for {self.category}"

        body = f"Attached is the arxiv summary PDF for this week in category {self.category}."
        msg.attach(MIMEText(body, "plain"))

        pdf_file = self.path + ".pdf"
        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"PDF file {pdf_file} does not exist.")

        try:
            with open(pdf_file, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(),_subtype="pdf")
                pdf_attachment.add_header("Content-Disposition","attachment",filename=pdf_file.split("/")[-1])
                msg.attach(pdf_attachment)
        except Exception as e:
            print(f"Error attaching PDF file '{pdf_file}': {e}")
            raise 
        
        try:
            server =  smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_RECEIVER, msg.as_string())
            print("Summary email sent successfully.")
        except Exception as e:
            print(f"Error sending email: {e}")
            raise

    def push_to_wechat(self):
        pass

    def push_error_message(self, exception):
        msg = MIMEMultipart()
        msg["From"] = MAIL_USER
        msg["To"] = MAIL_RECEIVER
        msg["Subject"] = f"Error in ArXiv Summarization Script"

        error_message = f"An error occurred:\n\n{exception}\n\n{traceback.format_exc()}"
        msg.attach(MIMEText(error_message,"plain"))

        try:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_RECEIVER, msg.as_string())
            print("Error email sent successfully.")
        except Exception as e:
            print(f"Error sending error email: {e}")


def main():
    pusher = Pusher()
    pusher.push_to_email()


if __name__ == "__main__":
    main()
