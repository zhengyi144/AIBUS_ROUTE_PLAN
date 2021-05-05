from datetime import datetime
from app.utils.core import db

class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'tbl_user'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(20), nullable=False)  # 用户姓名
    password=db.Column(db.String(255),nullable=False)
    role=db.Column(db.Integer(1),nullable=False) #管理员角色
    citycode=db.Column(db.String(20), nullable=False)

db.create_all()
    