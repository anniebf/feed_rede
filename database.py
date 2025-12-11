from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()

FUSO_HORARIO = pytz.timezone('America/Cuiaba')

# SOLUÇÃO 1: Usar timezone do PostgreSQL
def data_hora_local():
    """Retorna o datetime atual no fuso horário UTC-4:00."""
    return datetime.now(FUSO_HORARIO)

# SOLUÇÃO 2: Usar timezone do PostgreSQL diretamente na query
def agora_utc_menos_4():
    """Usa timezone do PostgreSQL para UTC-4."""
    # Retorna uma expressão SQL que usa timezone do banco
    return func.timezone('America/Cuiaba', func.now())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.String(200), default='')
    profile_pic = db.Column(db.String(200), default='default.png')
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False, default='text')
    media_path = db.Column(db.String(200))
    # Usa a função que retorna datetime local
    created_at = db.Column(db.DateTime, nullable=False, default=data_hora_local)
    likes = db.relationship('Like', backref='post_likes_link', lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user = db.relationship('User', backref='likes', lazy=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_uc'),)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # Usa a função que retorna datetime local
    created_at = db.Column(db.DateTime, default=data_hora_local)
    author = db.relationship('User', backref=db.backref('comment_author_links', lazy=True))