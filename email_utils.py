from flask import render_template, current_app
import yagmail
import csv
import time
import os
from premailer import transform
import re

def minify_html(html):
    """Remove unnecessary whitespace and line breaks from HTML"""
    html = re.sub(r'>\s+<', '><', html)  # Remove space between tags
    html = re.sub(r'\s{2,}', ' ', html)  # Collapse multiple spaces
    html = html.strip()
    return html

def create_email_body(first_name, last_name, company):
    # Use current_app context to render templates
    with current_app.app_context():
        mail_body = render_template('mail.html', first_name=first_name, last_name=last_name, company=company)
    # Inline styles and preserve <style> tags
    inlined_html = transform(
        mail_body,
        keep_style_tags=True,
        disable_leftover_css=False,
        strip_important=False
    )
    # Minify HTML to remove extra spaces (optional but best for Gmail)
    clean_html = minify_html(inlined_html)
    return clean_html

def send_emails_stream(subject, delay, filepath, sender_email, password, smtp_host=None, smtp_port=None):
    if smtp_host and smtp_port:
        yag = yagmail.SMTP(user=sender_email, password=password, host=smtp_host, port=smtp_port)
    else:
        yag = yagmail.SMTP(user=sender_email, password=password)

    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            recipient = row['email']
            first_name = row.get('first_name', '')
            last_name = row.get('last_name', '')
            company = row.get('company', '')

            body = create_email_body(first_name, last_name, company)
            count += 1
            try:
                yag.send(to=recipient, subject=subject, contents=body)
                message = f"Email {count} sent to {recipient}"
            except Exception as e:
                message = f"Failed to send email to {recipient}: {str(e)}"

            yield f"data: {message}\n\n"
            time.sleep(delay)
