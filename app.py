from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import db, User, Post
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-super-ultra-secreta-db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///socialfeed.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Extensões permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

db.init_app(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('feed'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('feed'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('feed'))
        else:
            return render_template('login.html', error='Credenciais inválidas')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('feed'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        bio = request.form.get('bio', '')

        # Verifica se o usuário já existe
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Nome de usuário já existe')

        # Processa a foto de perfil
        profile_pic = 'default.png'
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic = filename

        # Cria novo usuário
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            bio=bio,
            profile_pic=profile_pic
        )

        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = username
        return redirect(url_for('feed'))

    return render_template('register.html')


@app.route('/feed')
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Busca todos os posts ordenados por data
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('feed.html', posts=posts, username=session['username'])


@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form.get('content', '')
    post_type = request.form.get('type', 'text')

    new_post = Post(
        user_id=session['user_id'],
        content=content,
        type=post_type,
        created_at=datetime.utcnow()
    )

    # Processa arquivo se existir
    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(
                f"{session['user_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_post.media_path = filename

    db.session.add(new_post)
    db.session.commit()

    return redirect(url_for('feed'))


@app.route('/get_user_info/<int:user_id>')
def get_user_info(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'})

    user = User.query.get(user_id)
    if user:
        return jsonify({
            'username': user.username,
            'bio': user.bio,
            'profile_pic': url_for('static', filename=f'uploads/{user.profile_pic}')
        })
    return jsonify({'error': 'Usuário não encontrado'})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.before_request
def create_tables():
    # Cria as tabelas se não existirem
    with app.app_context():
        db.create_all()
        # Cria pasta de uploads se não existir
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)