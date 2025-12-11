from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.schema import UniqueConstraint

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.String(200), default='')
    profile_pic = db.Column(db.String(200), default='default.png')

    # 1. Mantenha o relacionamento principal aqui. Ele cria Post.author
    posts = db.relationship('Post', backref='author', lazy=True)
    # Propriedades adicionais: .comments (backref do Comment.author)
    # Propriedades adicionais: .likes (backref do Like.user)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False)  # 'text', 'image', 'video'
    media_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post_likes_link', lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    # Relacionamento que cria Like.user (o usuário que curtiu)
    user = db.relationship('User', backref='likes', lazy=True)
    # O relacionamento com Post já é criado em Post.likes. Não precisa de um segundo aqui.
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_uc'),)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    author = db.relationship('User', backref=db.backref('comment_author_links', lazy=True))
