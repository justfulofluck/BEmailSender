from flask import Flask, render_template, request, redirect, url_for
import yagmail
import csv
import time
import os

app = Flask(__name__)

# Homepage with form
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sender_email = request.form['sender_email']
        app_password = request.form['app_password']
        subject = request.form['subject']
        delay = int(request.form['delay'])
        file = request.files['csv_file']

        # Save uploaded CSV
        filepath = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)

        # Send emails
        results = []
        yag = yagmail.SMTP(sender_email, app_password)
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                recipient = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                company = row['company']
                body = f"""
                <p>hello {first_name} {last_name},</p>
                <p>this is test mail</p>
                <p>regards,</p>
                <p>BGT</p>
                """
                try:
                    yag.send(to=recipient, subject=subject, contents=body)
                    results.append(f"Email sent to {recipient}")
                except Exception as e:
                    results.append(f"Failed to send email to {recipient}: {str(e)}")
                time.sleep(delay)

        return render_template('result.html', results=results)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
