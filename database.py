from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()

FUSO_HORARIO = pytz.timezone('America/Cuiaba')


def data_hora_local():
    """Retorna o datetime atual no fuso horário UTC-4:00."""
    return datetime.now(FUSO_HORARIO)


def agora_utc_menos_4():
    """Usa timezone do PostgreSQL para UTC-4."""
    return func.timezone('America/Cuiaba', func.now())


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text, default='')
    profile_pic = db.Column(db.Text, default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # RELAÇÕES CORRIGIDAS (backrefs diferentes)
    posts = db.relationship('Post', backref='post_author', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='like_user', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='comment_author', lazy=True, cascade='all, delete-orphan')


class Post(db.Model):
    __tablename__ = 'posts'  # Adicione esta linha para consistência

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False, default='text')
    media_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=data_hora_local)

    # RELAÇÕES (backrefs diferentes dos de User)
    likes = db.relationship('Like', backref='like_post', lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='comment_post', lazy=True, cascade="all, delete-orphan")


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_uc'),)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=data_hora_local)