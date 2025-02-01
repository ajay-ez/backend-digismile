import os
from flask_cors import CORS
from flask_mail import Mail
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask import Flask, request
from flask_migrate import Migrate
from backend.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Load enviornment variable from .env file
load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_object(config_class)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    # app.config['MAIL_USERNAME'] = 'digismile.doc@gmail.com'
    # app.config['MAIL_PASSWORD'] = 'ghal rbyt ngnt raig'  # google pass: ghal rbyt ngnt raig
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') 
    app.config['MAIL_DEFAULT_SENDER'] = 'digismile.doc@gmail.com'
    # print("app->", app.config)
    mail = Mail(app)
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # @app.before_request
    # def ensure_content_length():
    #     request.environ.setdefault('CONTENT_LENGTH', '0')

    from backend.routes import main
    app.register_blueprint(main)

    return app