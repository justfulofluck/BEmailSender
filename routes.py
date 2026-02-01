from flask import Blueprint, render_template, request, Response, current_app, stream_with_context
import os
from email_utils import send_emails_stream
from settings_storage import save_email_settings, load_email_settings

main_routes = Blueprint('main', __name__)

@main_routes.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@main_routes.route('/settings', methods=['GET'])
def settings():
    return render_template('settings.html')

@main_routes.route('/help', methods=['GET'])
def help():
    return render_template('help.html')

@main_routes.route('/save_settings', methods=['POST'])
def save_settings():
    email_provider = request.form.get('email_provider')
    if email_provider not in ['gmail', 'custom']:
        return "invalid email provider selected ", 400

    if email_provider == 'gmail':
        sender_email = request.form.get('gmail_sender_email')
        password = request.form.get('gmail_app_password')
        smtp_host = None
        smtp_port = None
    elif email_provider == 'custom':
        sender_email = request.form.get('custom_sender_email')
        password = request.form.get('custom_password')
        smtp_host = request.form.get('custom_smtp_host')
        smtp_port = request.form.get('custom_smtp_port')
        if smtp_port:
            smtp_port = int(smtp_port)
        else:
            return "SMTP port is required for custom provider.", 400
    else:
        return "Invalid email provider selected.", 400

    save_email_settings({
        'sender_email': sender_email,
        'password': password,
        'smtp_host': smtp_host,
        'smtp_port': smtp_port
    })
    return render_template('settings.html')


@main_routes.route('/send_emails_stream', methods=['POST'])
def send_emails_stream_route():
    print("Form keys:", request.form.keys())
    print("Files keys:", request.files.keys())

    subject = request.form.get('subject')
    delay = float(request.form.get('delay', 1))
    file = request.files.get('csv_file')

    if not file or file.filename == '':
        return "No CSV file uploaded.", 400

    email_provider = request.form.get('email_provider')

    if email_provider == 'gmail':
        sender_email = request.form.get('gmail_sender_email')
        password = request.form.get('gmail_app_password')
        smtp_host = None
        smtp_port = None
    elif email_provider == 'custom':
        sender_email = request.form.get('custom_sender_email')
        password = request.form.get('custom_password')
        smtp_host = request.form.get('custom_smtp_host')
        smtp_port = request.form.get('custom_smtp_port')
        if smtp_port:
            smtp_port = int(smtp_port)
        else:
            return "SMTP port is required for custom provider.", 400
    else:
        return "Invalid email provider selected.", 400

    if not sender_email or not password:
        settings = load_email_settings()
        if settings:
            sender_email = settings.get('sender_email')
            password = settings.get('password')
            smtp_host = settings.get('smtp_host')
            smtp_port = settings.get('smtp_port')

    upload_dir = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    file.save(filepath)

    @stream_with_context
    def generate():
        yield from send_emails_stream(subject, delay, filepath, sender_email, password, smtp_host, smtp_port)

    return Response(generate(), mimetype='text/event-stream')
