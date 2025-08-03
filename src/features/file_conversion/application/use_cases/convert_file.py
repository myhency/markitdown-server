from ..ports.conversion_engine import ConversionEnginePort
from ..ports.file_storage import FileStoragePort
from ...domain.models.conversion_request import ConversionRequest
from ...domain.models.conversion_result import ConversionResult
from ...domain.services.markdown_enhancer import MarkdownEnhancerService
from ...domain.exceptions.conversion_exceptions import ConversionFailedException


class ConvertFileUseCase:
    
    def __init__(
        self,
        conversion_engine: ConversionEnginePort,
        file_storage: FileStoragePort,
        markdown_enhancer: MarkdownEnhancerService
    ):
        self._conversion_engine = conversion_engine
        self._file_storage = file_storage
        self._markdown_enhancer = markdown_enhancer
    
    def execute(self, request: ConversionRequest) -> ConversionResult:
        try:
            result = self._conversion_engine.convert(request.file_path)
            
            if not result or not result.text_content:
                raise ConversionFailedException("The file could not be converted to Markdown")
            
            markdown_content = result.text_content
            if request.enhance_markdown:
                markdown_content = self._markdown_enhancer.enhance_markdown_structure(
                    markdown_content, request.filename
                )
            
            return ConversionResult(
                success=True,
                markdown=markdown_content,
                original_markdown=result.text_content,
                title=getattr(result, 'title', None),
                metadata={
                    'original_filename': request.filename,
                    'converted_size': len(markdown_content),
                    'original_size': len(result.text_content),
                    'enhanced': request.enhance_markdown
                }
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                markdown="",
                error_message=str(e)
            )