import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import db, User, Post, Like, Comment, data_hora_local
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-super-ultra-secreta-db'

# ===== CONFIGURAÇÃO DO CLOUDINARY =====
cloudinary.config(
    cloud_name='drcktqjp7',  # Seu cloud name'
    api_key='448339431774236',     # Sua API key
    api_secret=os.getenv('api'),             # SUA API SECRET AQUI
    secure=True
)

# ===== CONFIGURAÇÕES ESSENCIAIS =====
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Extensões permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

# ===== CONFIGURAÇÃO DO BANCO DE DADOS =====
# Tenta pegar do ambiente primeiro
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Se tiver DATABASE_URL no ambiente (Render)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'options': '-c timezone=America/Cuiaba'
        }
    }
    # Corrige postgres:// para postgresql://
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://',
                                                                                              'postgresql://', 1)
    print("✅ Usando DATABASE_URL do ambiente")
else:

    user=os.getenv('USER')
    password=os.getenv('PASSWORD')
    host=os.getenv('HOST')
    port=os.getenv('PORT')
    db_name=os.getenv('DATABASE_NAME')
    # CORREÇÃO: URL correta do seu PostgreSQL no Render
    # O host parece estar com typos: "dpg-d4t1bo3ubrs73anp14g-a" vs "dpg-d4tibo3uibrs73anpi4g-a"
    # Usando a versão que parece correta baseada na sua URL

    app.config[
        'SQLALCHEMY_DATABASE_URI'] = f'{os.getenv('postgres')}'
    #   'SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user}:{password}{host}:{port}/{db_name}'
    print("✅ Usando configuração manual do PostgreSQL")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco
db.init_app(app)


# ===== FUNÇÃO PARA INICIALIZAR BANCO =====
def init_database():
    """Inicializa o banco de dados apenas uma vez."""
    with app.app_context():
        try:
            # Cria a pasta de uploads
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            print(f"📁 Pasta de uploads: {app.config['UPLOAD_FOLDER']}")

            # Cria as tabelas
            db.create_all()
            print("✅ Tabelas criadas/verificadas")

            # Testa a conexão
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT version();"))
                print(f"🔗 PostgreSQL: {result.fetchone()[0]}")

        except Exception as e:
            print(f"⚠️  Erro ao inicializar banco: {e}")


# Inicializa o banco ao iniciar
init_database()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ===== REMOVA O @app.before_request ANTIGO =====
# NÃO use @app.before_request para criar tabelas!

# ===== ROTAS =====
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

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Nome de usuário já existe')

        # URL padrão do Cloudinary (ou uma imagem default no Cloudinary)
        profile_pic_url = 'https://res.cloudinary.com/drcktqjp7/image/upload/v1700000000/default_profile.png'

        # Se o usuário enviou foto no registro
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename):
                # UPLOAD PARA CLOUDINARY
                upload_result = cloudinary.uploader.upload(
                    file,
                    public_id=f"postaai/user_{username}_register",
                    folder="postaai/profile_pics",
                    transformation=[
                        {'width': 300, 'height': 300, 'crop': 'fill', 'gravity': 'face'},
                        {'quality': 'auto:good'}
                    ]
                )
                profile_pic_url = upload_result['secure_url']

        # Cria novo usuário com URL do Cloudinary
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            bio=bio,
            profile_pic=profile_pic_url  # ✅ Armazena URL completa
        )

        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = username
        return redirect(url_for('feed'))

    return render_template('register.html')


@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Não autenticado'}), 401

        if 'profile_pic_file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400

        file = request.files['profile_pic_file']
        user_id = session['user_id']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400

        if file and allowed_file(file.filename):
            # --- CLOUDINARY UPLOAD ---
            # Lê o arquivo em memória
            file_bytes = file.read()

            # Nome único para o arquivo no Cloudinary
            public_id = f"postaai/user_{user_id}_profile"

            # Faz upload para o Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_bytes,
                public_id=public_id,
                folder="postaai/profile_pics",
                overwrite=True,  # Substitui se já existir
                transformation=[
                    {'width': 300, 'height': 300, 'crop': 'fill', 'gravity': 'face'},
                    {'quality': 'auto:good'},
                    {'fetch_format': 'auto'}
                ]
            )

            # URL segura da imagem
            cloudinary_url = upload_result['secure_url']
            print(f"✅ Foto enviada para Cloudinary: {cloudinary_url}")

            # Atualiza no banco de dados
            user = User.query.get(user_id)
            if user:
                # Armazena a URL do Cloudinary no banco
                user.profile_pic = cloudinary_url  # Agora armazena URL completa
                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': 'Foto atualizada com sucesso!',
                    'new_pic_url': cloudinary_url  # Retorna URL completa
                })
            else:
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        else:
            return jsonify({'success': False, 'message': 'Extensão não permitida'}), 400

    except Exception as e:
        print(f"❌ ERRO NO UPLOAD: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500


@app.route('/feed')
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    current_user = User.query.get(user_id)

    if not current_user:
        session.clear()
        return redirect(url_for('login'))

    profile_pic_filename = current_user.profile_pic

    # MÉTODO ALTERNATIVO: Busca tudo separadamente
    # Busca todos os posts
    all_posts = Post.query.order_by(Post.created_at.desc()).all()

    # Busca autores para cada post
    posts_with_info = []
    for post in all_posts:
        # Busca o autor do post
        author = User.query.get(post.user_id)

        # Conta likes
        likes_count = Like.query.filter_by(post_id=post.id).count()

        # Verifica se o usuário atual curtiu
        is_liked_by_user = Like.query.filter_by(
            post_id=post.id,
            user_id=user_id
        ).first() is not None

        # Busca comentários para este post
        comments = Comment.query.filter_by(post_id=post.id) \
            .order_by(Comment.created_at.asc()) \
            .all()

        # Adiciona autor e comentários ao objeto post
        post.author = author
        post.comments = comments
        post.likes_count = likes_count
        post.is_liked_by_user = is_liked_by_user

        posts_with_info.append(post)

    return render_template(
        'feed.html',
        posts=posts_with_info,
        username=session['username'],
        my_profile_pic=profile_pic_filename,
        Comment=Comment
    )


@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form.get('content', '')
    post_type = 'text'
    media_url = None

    # Processa arquivo
    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename != '' and allowed_file(file.filename):
            # UPLOAD PARA CLOUDINARY
            extension = file.filename.rsplit('.', 1)[1].lower()
            post_type = 'video' if extension in ['mp4', 'mov', 'avi'] else 'image'

            resource_type = "video" if post_type == 'video' else "image"

            upload_result = cloudinary.uploader.upload(
                file,
                resource_type=resource_type,
                public_id=f"postaai/post_{session['user_id']}_{int(datetime.utcnow().timestamp())}",
                folder=f"postaai/posts/{resource_type}s",
                transformation=[
                    {'width': 1200, 'crop': 'limit'} if post_type == 'image' else {},
                    {'quality': 'auto:good'}
                ]
            )

            media_url = upload_result['secure_url']

    new_post = Post(
        user_id=session['user_id'],
        content=content,
        type=post_type,
        media_path=media_url  # ✅ Armazena URL do Cloudinary
    )

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


@app.route('/toggle_like/<int:post_id>', methods=['POST'])
def toggle_like(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401

    user_id = session['user_id']
    existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()

    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        new_like = Like(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        liked = True

    db.session.commit()
    total_likes = Like.query.filter_by(post_id=post_id).count()

    return jsonify({
        'success': True,
        'liked': liked,
        'likes_count': total_likes
    })


@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401

    content = request.json.get('content')

    if not content or not content.strip():
        return jsonify({'success': False, 'message': 'Comentário vazio'}), 400

    user_id = session['user_id']

    new_comment = Comment(
        user_id=user_id,
        post_id=post_id,
        content=content.strip()
    )

    db.session.add(new_comment)
    db.session.commit()

    comment_data = {
        'username': session['username'],
        'content': new_comment.content,
        'comments_count': Comment.query.filter_by(post_id=post_id).count()
    }

    return jsonify({
        'success': True,
        'message': 'Comentário adicionado',
        'comment': comment_data
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/status')
def status():
    """Rota para verificar status do app."""
    try:
        user_count = User.query.count()
        post_count = Post.query.count()
        return jsonify({
            'status': 'online',
            'users': user_count,
            'posts': post_count,
            'database': 'conectado'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


if __name__ == '__main__':
    # Cria estrutura se necessário
    with app.app_context():
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    print(f"🚀 Servidor iniciando...")
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🔗 Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

    app.run(debug=True, host='0.0.0.0', port=8080)