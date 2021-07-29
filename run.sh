# 启动FlaskAPP
nohup gunicorn -c config/gun.conf run:app &