from flask import Flask
from ..infrastructure.config.settings import AppSettings
from ..infrastructure.utils.logger import setup_logging
from .controllers.file_conversion_controller import file_conversion_bp
from .controllers.health_controller import health_bp
from .controllers.error_handlers import register_error_handlers
from .dependency_injection import DependencyContainer


def create_app(settings: AppSettings = None) -> Flask:
    if settings is None:
        settings = AppSettings()
    
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = settings.json_as_ascii
    app.config['MAX_CONTENT_LENGTH'] = settings.max_content_length
    
    setup_logging()
    
    container = DependencyContainer()
    app.container = container
    
    app.register_blueprint(file_conversion_bp)
    app.register_blueprint(health_bp)
    
    register_error_handlers(app)
    
    return app