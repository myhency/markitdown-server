from flask import Flask
from ..shared.infrastructure.config.settings import AppSettings
from ..shared.infrastructure.utils.logger import setup_logging
from ..features.file_conversion.web.controllers.file_conversion_controller import file_conversion_bp
from ..features.health.web.controllers.health_controller import health_bp
from ..shared.web.common.error_handlers import register_error_handlers
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