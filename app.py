import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///../instance/site.db')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure instance and upload directories exist
os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

# --- Extensions ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='viewer')  # 'admin' or 'viewer'
    magic_token = db.Column(db.String(100), unique=True, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_magic_token(self):
        self.magic_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.magic_token

class SiteConfig(db.Model):
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), default='text') # 'text', 'image', 'number'

# --- Helpers ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_config_dict():
    configs = SiteConfig.query.all()
    return {c.key: c.value for c in configs}

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(role='admin').first():
            print("Creating default admin user...")
            admin = User(username='admin', role='admin')
            admin.set_password('admin') # Default, should be changed
            db.session.add(admin)
            
        # Initialize default config keys if missing
        defaults = {
            'page_title': 'Unsere Story | Friendship Wrapped',
            'title_main': 'UNSERE<br>STORY',
            'intro_text': 'Bereit für eine Zeitreise durch unsere Freundschaft?',
            'birthday_title': 'Happy Birthday!',
            'birthday_age': '19',
            'birthday_text': 'Heute feiern wir dich und all die Jahre, die wir uns schon kennen!',
            'stats_title': 'Unsere Zeit',
            'years_count': '5',
            'days_count': '1825',
            'stats_subtitle': 'Tage voller Erinnerungen',
            'chat_stats_title': 'Einfach unzertrennlich',
            'chat_stats_config': 'message-circle|45230|Nachrichten\nphone-call|840|Stunden Telefonate\nimage|2150|Geteilte Medien',
            'wa_title': 'Deine legendären Nachrichten',
            'wa_messages': 'Hahahah ich kann nicht mehr 😂\nBin in 5 Minuten da! (Versprochen)\nWas essen wir heute? Ich sterbe 🍕\nGlaub nicht was gerade passiert ist...\nLove you Bestie! 💖✨',
            'development_title': 'Die Entwicklung',
            'img_then': 'https://images.unsplash.com/photo-1543269865-cbf427effbad?w=800',
            'img_now': 'https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=800',
            'chaos_title': 'Unsere Chaos-Momente',
            'music_title': 'Euer All-Time Favorit',
            'song_title': 'Friendship Anthem',
            'song_artist': 'Dauerschleife',
            'song_cover': 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400',
            'highlight_label': 'Das Highlight',
            'trip_city': 'Paris Vibes',
            'trip_bg': 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200',
            'gallery_paris': 'https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?w=600,https://images.unsplash.com/photo-1549144511-f099e773c147?w=600,https://images.unsplash.com/photo-1503917988258-f87a78e3c995?w=600,https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=600',
            'gallery_memes': 'https://images.unsplash.com/photo-1531928351158-2f7360b94b51?w=600,https://images.unsplash.com/photo-1506863530036-1efeddceb993?w=600,https://images.unsplash.com/photo-1543332164-6e82f355badc?w=600',
            'bucket_title': 'Was wir noch erleben',
            'analyzing_text': 'Analysiere Freundschaft...',
            'character_type_label': 'Charakter-Typ',
            'character_type': 'Elite-Bestie',
            'character_name': 'Simon',
            'postits_title': 'Gründe, warum du toll bist',
            'postits_content': 'Du bist die Beste!,Dein Lachen ist ansteckend,Beste Reisebegleitung,Immer ein offenes Ohr,Chaos-Queen (positiv!),Einfach du selbst ❤️',
            'final_msg_title': 'Bestie Forever.',
            'final_msg_text': 'Danke für jeden einzelnen Moment. Du bist Familie. Auf ewig!',
            'final_sender_name': 'Deine [Dein Name]',
            'show_birthday': 'true',
            'show_stats': 'true',
            'show_whatsapp': 'true',
            'show_development': 'true',
            'show_chaos': 'true',
            'show_music': 'true',
            'show_highlights': 'true',
            'show_postits': 'true',
            'show_character': 'true'
        }
        
        for key, val in defaults.items():
            if not SiteConfig.query.get(key):
                db.session.add(SiteConfig(key=key, value=val))
        
        db.session.commit()

# --- Routes ---
@app.route('/')
@login_required
def index():
    config = get_config_dict()
    return render_template('index.html', config=config)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login fehlgeschlagen. Bitte überprüfe deine Daten.')
            
    return render_template('login.html')

@app.route('/magic/<token>')
def magic_login(token):
    user = User.query.filter_by(magic_token=token).first()
    if user:
        login_user(user)
        return redirect(url_for('index'))
    return "Ungültiger oder abgelaufener Link", 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    if request.method == 'POST':
        # Handle Config Updates
        for key in request.form:
            if key.startswith('config_'):
                config_key = key.replace('config_', '')
                config_entry = SiteConfig.query.get(config_key)
                if config_entry:
                    config_entry.value = request.form[key]
                    
        # Handle Image Uploads
        for key in request.files:
            file = request.files[key]
            if file and file.filename != '':
                filename = secure_filename(f"{key}_{secrets.token_hex(4)}_{file.filename}")
                file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
                
                # Update DB
                config_key = key.replace('file_', '')
                config_entry = SiteConfig.query.get(config_key)
                if not config_entry:
                     config_entry = SiteConfig(key=config_key, value='', type='image')
                     db.session.add(config_entry)
                
                config_entry.value = url_for('static', filename=f'uploads/{filename}')

        db.session.commit()
        flash('Einstellungen gespeichert!')
        return redirect(url_for('admin_dashboard'))

    configs = SiteConfig.query.all()
    users = User.query.all()
    host_url = request.host_url.rstrip('/')
    return render_template('admin.html', configs=configs, users=users, host_url=host_url)

@app.route('/admin/api/update', methods=['POST'])
@admin_required
def api_update_config():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    if not key:
        return {"error": "Key missing"}, 400
        
    config_entry = SiteConfig.query.get(key)
    if config_entry:
        config_entry.value = value
        db.session.commit()
        return {"success": True}
    
    return {"error": "Config not found"}, 404

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    username = request.form.get('username')
    # Random password for link-only users, or set specific one
    password = secrets.token_urlsafe(8) 
    
    if User.query.filter_by(username=username).first():
        flash('Benutzer existiert bereits!')
        return redirect(url_for('admin_dashboard'))
        
    new_user = User(username=username, role='viewer')
    new_user.set_password(password)
    new_user.generate_magic_token()
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'Benutzer {username} erstellt!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/link/<int:user_id>')
@admin_required
def generate_link(user_id):
    user = User.query.get_or_404(user_id)
    token = user.generate_magic_token()
    return redirect(url_for('admin_dashboard'))

# Application bootstrapping
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0')
else:
    # For Gunicorn
    init_db()
