from datetime import datetime
from app.utils.core import db

class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'tbl_user'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(250),unique=True, nullable=False)  # 用户姓名
    password=db.Column(db.String(255),nullable=False)
    role=db.Column(db.Integer(),nullable=False) #管理员角色
    citycode=db.Column(db.String(20), nullable=False)

    def __init__(self,userName,password,citycode,role):
        self.username=userName
        self.password=password
        self.role=role
        self.citycode=citycode
    
    def getByUserName(self,userName,password):
        return self.query.filter_by(username=userName,password=password).first()
    
    def add(self, user):
        db.session.add(user)
        return session_commit()

#db.create_all()
    