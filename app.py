from flask import Flask, render_template, request, Response
from dotenv import load_dotenv
import yagmail
import csv
import time
import os

load_dotenv()

app = Flask(__name__)

# Load credentials from .env
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
APP_PASSWORD = os.getenv('APP_PASSWORD')

def create_email_body(first_name, last_name, company):
    # Push app context here to fix "working outside of application context" error
    with app.app_context():
        mail_body = render_template('mail.html', first_name=first_name, last_name=last_name, company=company)
        signature = render_template('signature.html')
    return mail_body + signature

def send_emails_stream(subject, delay, filepath):
    yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            recipient = row['email']
            first_name = row['first_name']
            last_name = row['last_name']
            company = row['company']

            body = create_email_body(first_name, last_name, company)
            count += 1
            try:
                yag.send(to=recipient, subject=subject, contents=body)
                message = f"Email {count} sent to {recipient}"
            except Exception as e:
                message = f"Failed to send email to {recipient}: {str(e)}"
            # Yield SSE formatted message
            yield f"data: {message}\n\n"
            time.sleep(delay)

@app.route('/', methods=['GET'])
def index():
    # Serve the email sending form
    return render_template('index.html')

@app.route('/send_emails_stream', methods=['POST'])
def send_emails_stream_route():
    subject = request.form.get('subject')
    delay = float(request.form.get('delay', 1))
    file = request.files.get('csv_file')

    if not file or file.filename == '':
        return "No CSV file uploaded.", 400

    filepath = os.path.join('uploads', file.filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(filepath)

    return Response(send_emails_stream(subject, delay, filepath), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True)
