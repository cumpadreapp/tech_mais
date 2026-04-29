from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'techmais_secret_key_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tech_mais.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/uploads/banners', exist_ok=True)
os.makedirs('static/uploads/posts', exist_ok=True)

# Modelos do Banco de Dados
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(50), default='text')  # text, image, video, youtube
    media_url = db.Column(db.String(500))
    youtube_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'post_type': self.post_type,
            'media_url': self.media_url,
            'youtube_id': self.youtube_id,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
            'formatted_date': self.created_at.strftime('%d de %B, %Y')
        }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Criar admin padrão se não existir
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('tech@admin2024'),
            email='admin@techmais.com'
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado com sucesso!")
        print("Usuário: admin")
        print("Senha: tech@admin2024")

# Rotas da aplicação
@app.route('/')
def index():
    banner = Banner.query.filter_by(active=True).first()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', banner=banner, posts=posts)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Bem-vindo de volta, {username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('❌ Usuário ou senha incorretos!', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Você saiu do painel administrativo!', 'info')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    banner = Banner.query.filter_by(active=True).first()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin_dashboard.html', banner=banner, posts=posts)

@app.route('/admin/update_banner', methods=['POST'])
@login_required
def update_banner():
    image_url = None
    
    # Upload da imagem do banner
    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"banner_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join('static/uploads/banners', filename)
            file.save(filepath)
            image_url = f'/static/uploads/banners/{filename}'
    
    banner = Banner.query.filter_by(active=True).first()
    if banner:
        if image_url:
            banner.image_url = image_url
        banner.updated_at = datetime.utcnow()
    else:
        banner = Banner(
            image_url=image_url
        )
        db.session.add(banner)
    
    db.session.commit()
    flash('Banner atualizado com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/create_post', methods=['POST'])
@login_required
def create_post():
    title = request.form.get('title')
    content = request.form.get('content')
    post_type = request.form.get('post_type', 'text')
    youtube_id = request.form.get('youtube_id')
    
    media_url = None
    
    # Upload de arquivo de mídia
    if 'media_file' in request.files:
        file = request.files['media_file']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join('static/uploads/posts', filename)
            file.save(filepath)
            media_url = f'/static/uploads/posts/{filename}'
    
    post = Post(
        title=title,
        content=content,
        post_type=post_type,
        media_url=media_url,
        youtube_id=youtube_id
    )
    
    db.session.add(post)
    db.session.commit()
    flash('Postagem criada com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Postagem removida com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/get_post/<int:post_id>')
@login_required
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    return jsonify(post.to_dict())

if __name__ == '__main__':
    app.run(debug=True)