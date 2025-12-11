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


@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    try:  # <--- INÍCIO DO TRATAMENTO DE ERROS
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Não autenticado'}), 401

        # O nome do input no HTML é 'profile_pic_file'
        if 'profile_pic_file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400

        file = request.files['profile_pic_file']
        user_id = session['user_id']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400

        if file and allowed_file(file.filename):

            file_ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}")

            # 2. Salvar o arquivo no disco (Pode falhar por permissão/caminho)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)  # <--- ERRO DE PERMISSÃO OU DISCO GERALMENTE OCORRE AQUI

            # 3. Atualizar o banco de dados
            user = User.query.get(user_id)
            if user:
                # Opcional: Remover a foto antiga
                if user.profile_pic != 'default.png':
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                user.profile_pic = filename
                db.session.commit()

                new_pic_url = url_for('static', filename=f'uploads/{filename}')
                return jsonify(
                    {'success': True, 'message': 'Foto de perfil atualizada com sucesso', 'new_pic_url': new_pic_url})
            else:
                os.remove(save_path)
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        else:
            return jsonify({'success': False, 'message': 'Extensão de arquivo não permitida'}), 400

    except Exception as e:
        # FIM DO TRATAMENTO DE ERROS: Isso garante que a resposta seja SEMPRE JSON
        # Imprime o erro no seu console do terminal para depuração
        print(f"ERRO CRÍTICO NO UPLOAD DE PERFIL (app.py): {e}")
        # Tenta reverter qualquer transação de banco de dados
        try:
            db.session.rollback()
        except:
            pass  # Ignora se a sessão não estiver ativa

        return jsonify({'success': False, 'message': f'Erro interno do servidor. Consulte o console.'}), 500

@app.route('/feed')
def feed():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 1. Buscar o usuário logado
    current_user = User.query.get(session['user_id'])

    # Garantir que o usuário foi encontrado (boa prática)
    if not current_user:
        # Se o ID na sessão for inválido, limpa a sessão e redireciona
        session.clear()
        return redirect(url_for('login'))

    # 2. Obter o nome do arquivo da foto de perfil
    profile_pic_filename = current_user.profile_pic

    # 3. Buscar todos os posts ordenados por data
    posts = Post.query.order_by(Post.created_at.desc()).all()

    # 4. Passar a variável extra para o template
    return render_template(
        'feed.html',
        posts=posts,
        username=session['username'],
        # NOVO CONTEXTO: Passa o nome do arquivo da foto de perfil
        my_profile_pic=profile_pic_filename
    )


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
    app.run(debug=True, host='0.0.0.0', port=8080)