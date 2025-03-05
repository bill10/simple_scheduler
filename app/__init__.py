import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .scheduler import init_scheduler
from .task_executor import init_executor
from .models.models import db

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SCRIPTS_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
    app.config['LOGS_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

    # Ensure required directories exist
    os.makedirs(app.config['SCRIPTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOGS_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize scheduler and task executor
    app.scheduler = init_scheduler(app)
    init_executor(app)

    with app.app_context():
        # Import routes
        from .routes import task_routes, frontend_routes
        app.register_blueprint(task_routes.bp)
        app.register_blueprint(frontend_routes.bp)

        # Create database tables if they don't exist
        with app.app_context():
            db.create_all()

    return app
