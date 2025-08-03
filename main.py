from src.web.app import create_app
from src.shared.infrastructure.config.settings import AppSettings
from src.shared.infrastructure.utils.file_utils import SUPPORTED_EXTENSIONS


def main():
    settings = AppSettings()
    app = create_app(settings)
    
    print("🚀 MarkItDown File Converter Server Starting...")
    print("📁 Supported file formats:", ', '.join(sorted(SUPPORTED_EXTENSIONS)))
    print("🖼️  AI convertible formats:", ', '.join(sorted({'.pdf', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'})))
    print("   - PDF: Direct page-by-page conversion")
    print("   - Office files: Convert to PDF first, then to images") 
    print("   - PowerPoint/Word/Excel: [File] → PDF → Images → AI Analysis")
    print(f"🌐 Server will be available at: http://localhost:{settings.port}")
    print(f"📖 API documentation: http://localhost:{settings.port}")
    
    app.run(
      host=settings.host,
      port=settings.port,
      debug=settings.debug,
      use_reloader=False  # True에서 False로 변경
  )


if __name__ == '__main__':
    main()