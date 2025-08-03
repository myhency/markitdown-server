from ..ports.conversion_engine import LLMConversionEnginePort
from ..ports.ai_client import AIClientPort
from ..ports.file_storage import FileStoragePort
from ...domain.models.conversion_request import AIConversionRequest
from ...domain.models.conversion_result import ConversionResult
from ...domain.services.markdown_enhancer import MarkdownEnhancerService
from ...domain.exceptions.conversion_exceptions import ConversionFailedException, AIClientException


class ConvertImageUseCase:
    
    def __init__(
        self,
        llm_conversion_engine: LLMConversionEnginePort,
        ai_client: AIClientPort,
        file_storage: FileStoragePort,
        markdown_enhancer: MarkdownEnhancerService
    ):
        self._llm_conversion_engine = llm_conversion_engine
        self._ai_client = ai_client
        self._file_storage = file_storage
        self._markdown_enhancer = markdown_enhancer
    
    def execute(self, request: AIConversionRequest) -> ConversionResult:
        try:
            azure_client = self._ai_client.create_client(
                request.azure_endpoint,
                request.api_key,
                request.api_version
            )
            
            result = self._llm_conversion_engine.convert_with_llm(
                request.file_path,
                azure_client,
                request.deployment_name
            )
            
            if not result or not result.text_content:
                raise ConversionFailedException("The image could not be converted to Markdown with LLM")
            
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
                    'enhanced': request.enhance_markdown,
                    'llm_used': True,
                    'llm_model': request.deployment_name,
                    'azure_endpoint': request.azure_endpoint
                }
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                markdown="",
                error_message=str(e)
            )