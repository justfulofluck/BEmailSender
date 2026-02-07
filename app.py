from flask import Flask, render_template, request, Response, redirect, flash
from dotenv import load_dotenv
import json
import os
import secrets
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid # Keep secrets as it might be used elsewhere or intended to be kept

load_dotenv()

# Config file path
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file, falling back to empty dict."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_config(data):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load initial config or env vars
config = load_config()
SENDER_EMAIL = config.get('gmail_sender_email') or config.get('custom_sender_email') or os.getenv('SENDER_EMAIL')
APP_PASSWORD = config.get('gmail_app_password') or config.get('custom_password') or os.getenv('APP_PASSWORD')

# Initialize DB extension
db = SQLAlchemy()

# Models
class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body_content = db.Column(db.Text, nullable=False) # HTML content

class SentEmail(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    status = db.Column(db.String(20)) # 'sent', 'failed'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    opened_at = db.Column(db.DateTime, nullable=True) # For tracking

class ScheduledJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_at = db.Column(db.DateTime, nullable=False)
    recipient_file_path = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending') # 'pending', 'completed', 'cancelled'
    
def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)
    
    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    def send_emails_stream(subject, delay, filepath, attachments=None, template_id=None):
        # Reload config to get latest credentials
        current_config = load_config()
        provider = current_config.get('email_provider', 'gmail')
        
        sender_email = None
        password = None
        smtp_host = None
        smtp_port = None
        
        if provider == 'gmail':
            sender_email = current_config.get('gmail_sender_email') or os.getenv('SENDER_EMAIL')
            password = current_config.get('gmail_app_password') or os.getenv('APP_PASSWORD')
        else:
            sender_email = current_config.get('custom_sender_email')
            password = current_config.get('custom_password')
            smtp_host = current_config.get('custom_smtp_host')
            smtp_port = current_config.get('custom_smtp_port')
            
        if not sender_email or not password:
             yield f"data: Error: Email credentials not configured. Please check Settings.\n\n"
             return

        # Fetch template content if template_id is provided
        template_body = None
        if template_id:
            with app.app_context():
                template = EmailTemplate.query.get(template_id)
                if template:
                    template_body = template.body_content
                else:
                    yield f"data: Error: Selected template not found.\n\n"
                    return
        
        try:
            if provider == 'gmail':
                 yag = yagmail.SMTP(sender_email, password)
            else:
                 port = int(smtp_port) if smtp_port else 587
                 yag = yagmail.SMTP(sender_email, password, host=smtp_host, port=port)
        except Exception as e:
            yield f"data: Error connecting to SMTP server: {str(e)}\n\n"
            return

        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                recipient = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                company = row['company']

                # Use template body if available, otherwise default
                if template_body:
                    # Basic Jinja2-style replacement
                    body = template_body.replace('{{ first_name }}', first_name)\
                                        .replace('{{ last_name }}', last_name)\
                                        .replace('{{ company }}', company)\
                                        .replace('{{ name }}', first_name) # Common alias
                else:
                    body = create_email_body(first_name, last_name, company)
                    
                count += 1
                try:
                    yag.send(to=recipient, subject=subject, contents=body, attachments=attachments)
                    message = f"Email {count} sent to {recipient}"
                except Exception as e:
                    message = f"Failed to send email to {recipient}: {str(e)}"
                # Yield SSE formatted message
                yield f"data: {message}\n\n"
                time.sleep(delay)
    @app.route('/', methods=['GET'])
    def index():
        # Serve the email sending form, pass available templates
        templates = EmailTemplate.query.all()
        return render_template('index.html', templates=templates)

    @app.route('/help')
    def help_page():
        return render_template('help.html')

    @app.route('/settings', methods=['GET'])
    def settings_page():
        current_config = load_config() # Use a different variable name to avoid conflict with global 'config'
        return render_template('settings.html', config=current_config)

    @app.route('/save_settings', methods=['POST'])
    def save_settings_route():
        # Helper to safely get form data
        data = {
            'email_provider': request.form.get('email_provider'),
            'gmail_sender_email': request.form.get('gmail_sender_email'),
            'gmail_app_password': request.form.get('gmail_app_password'),
            'custom_sender_email': request.form.get('custom_sender_email'),
            'custom_password': request.form.get('custom_password'),
            'custom_smtp_host': request.form.get('custom_smtp_host'),
            'custom_smtp_port': request.form.get('custom_smtp_port'),
        }
        save_config(data)
        # Re-render settings with success message
    @app.route('/send_emails_stream', methods=['POST'])
    def send_emails_stream_route():
        subject = request.form.get('subject')
        delay = float(request.form.get('delay', 1))
        file = request.files.get('csv_file')
        uploaded_files = request.files.getlist('attachments')
        template_id = request.form.get('template_id')
        
        if template_id:
             template_id = int(template_id)

        if not file or file.filename == '':
            return "No CSV file uploaded.", 400

        filepath = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        
        attachment_paths = []
        if uploaded_files:
            for f in uploaded_files:
                if f.filename != '':
                    safe_name = os.path.basename(f.filename) 
                    att_path = os.path.join('uploads', safe_name)
                    f.save(att_path)
                    attachment_paths.append(att_path)

        return Response(send_emails_stream(subject, delay, filepath, attachment_paths, template_id), mimetype='text/event-stream')

    @app.route('/templates')
    def templates_list():
        templates = EmailTemplate.query.all()
        return render_template('templates_list.html', templates=templates)

    @app.route('/template/new')
    def new_template():
        return render_template('template_form.html')

    @app.route('/template/edit/<int:id>')
    def edit_template(id):
        template = EmailTemplate.query.get_or_404(id)
        return render_template('template_form.html', template=template)

    @app.route('/template/delete/<int:id>')
    def delete_template(id):
        template = EmailTemplate.query.get_or_404(id)
        db.session.delete(template)
        db.session.commit()
        return redirect('/templates')

    @app.route('/save_template', methods=['POST'])
    def save_template():
        id = request.form.get('id')
        name = request.form.get('name')
        subject = request.form.get('subject')
        body = request.form.get('body_content')
        
        if id:
             template = EmailTemplate.query.get_or_404(id)
             template.name = name
             template.subject = subject
             template.body_content = body
        else:
             new_template = EmailTemplate(name=name, subject=subject, body_content=body)
             db.session.add(new_template)
        
        db.session.commit()
        return redirect('/templates')

    # If main_routes blueprint is still needed, ensure it's defined and imported correctly
    # from routes import main_routes
    # app.register_blueprint(main_routes)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", debug=True)
