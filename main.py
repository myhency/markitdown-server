from src.web.app import create_app
from src.shared.infrastructure.config.settings import AppSettings

# WSGI application for production
app = create_app()

def main():
    """개발 환경에서만 사용하는 함수"""
    settings = AppSettings()
    app = create_app(settings)
    
    print("🚀 MarkItDown File Converter Server Starting (Development Mode)...")
    print("⚠️  For production, use: gunicorn main:app")
    
    app.run(
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        use_reloader=False
    )


if __name__ == '__main__':
    main()