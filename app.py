from flask import Flask, render_template, request
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
    # Render main mail content with placeholders replaced
    mail_body = render_template('mail.html', first_name=first_name, last_name=last_name, company=company)
    # Render signature
    signature = render_template('signature.html')
    # Combine and return full HTML body
    return mail_body + signature

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Use credentials from .env instead of form inputs
        subject = request.form['subject']
        delay = int(request.form['delay'])
        file = request.files.get('csv_file')

        # Validate CSV file uploaded
        if not file or file.filename == '':
            error_msg = "No CSV file uploaded."
            return render_template('index.html', error=error_msg)

        # Save uploaded CSV
        filepath = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)

        results = []
        yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)

        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                recipient = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                company = row['company']

                # Create body using templates
                body = create_email_body(first_name, last_name, company)

                try:
                    yag.send(to=recipient, subject=subject, contents=body)
                    results.append(f"Email sent to {recipient}")
                except Exception as e:
                    results.append(f"Failed to send email to {recipient}: {str(e)}")

                time.sleep(delay)

        return render_template('result.html', results=results)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
