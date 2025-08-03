import logging
from typing import List
from ..ports.ai_client import AIClientPort
from ..ports.image_processor import ImageProcessorPort
from ..ports.file_storage import FileStoragePort
from ...domain.models.conversion_request import AIConversionRequest
from ...domain.models.conversion_result import AIConversionResult, AIAnalysisResult
from ...domain.services.markdown_enhancer import MarkdownEnhancerService
from ...domain.exceptions.conversion_exceptions import ConversionFailedException, AIClientException

logger = logging.getLogger(__name__)


class ConvertWithAIUseCase:
    
    def __init__(
        self,
        ai_client: AIClientPort,
        image_processor: ImageProcessorPort,
        file_storage: FileStoragePort,
        markdown_enhancer: MarkdownEnhancerService
    ):
        self._ai_client = ai_client
        self._image_processor = image_processor
        self._file_storage = file_storage
        self._markdown_enhancer = markdown_enhancer
    
    def execute(self, request: AIConversionRequest) -> AIConversionResult:
        try:
            azure_client = self._ai_client.create_client(
                request.azure_endpoint, 
                request.api_key, 
                request.api_version
            )
            
            extension = request.filename.lower().split('.')[-1]
            extension = f'.{extension}'
            
            image_bytes_list = self._convert_document_to_images(
                request.file_path, extension, request.dpi
            )
            
            analysis_results = []
            markdown_pages = []
            
            for i, image_bytes in enumerate(image_bytes_list):
                try:
                    page_markdown = self._ai_client.analyze_image(
                        image_bytes, azure_client, request.deployment_name, i + 1
                    )
                    markdown_pages.append(page_markdown)
                    analysis_results.append(AIAnalysisResult(
                        page=i + 1,
                        status='success',
                        content_length=len(page_markdown)
                    ))
                    logger.info(f"Successfully analyzed page {i + 1}")
                
                except Exception as e:
                    error_markdown = f"# Page {i + 1}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
                    markdown_pages.append(error_markdown)
                    analysis_results.append(AIAnalysisResult(
                        page=i + 1,
                        status='error',
                        error=str(e)
                    ))
                    logger.error(f"Failed to analyze page {i + 1}: {str(e)}")
            
            combined_markdown = "\n\n---\n\n".join(markdown_pages)
            
            if request.enhance_markdown:
                combined_markdown = self._markdown_enhancer.enhance_markdown_structure(
                    combined_markdown, request.filename
                )
            
            successful_pages = len([r for r in analysis_results if r.status == 'success'])
            failed_pages = len([r for r in analysis_results if r.status == 'error'])
            
            return AIConversionResult(
                success=True,
                markdown=combined_markdown,
                analysis_results=analysis_results,
                pages_processed=len(image_bytes_list),
                successful_pages=successful_pages,
                failed_pages=failed_pages,
                metadata={
                    'original_filename': request.filename,
                    'converted_size': len(combined_markdown),
                    'enhanced': request.enhance_markdown,
                    'method': 'ai_image_analysis',
                    'llm_model': request.deployment_name,
                    'azure_endpoint': request.azure_endpoint,
                    'dpi': request.dpi if extension == '.pdf' else None
                }
            )
            
        except Exception as e:
            return AIConversionResult(
                success=False,
                markdown="",
                error_message=str(e),
                analysis_results=[],
                pages_processed=0,
                successful_pages=0,
                failed_pages=0
            )
    
    def _convert_document_to_images(self, file_path: str, extension: str, dpi: int) -> List[bytes]:
        if extension == '.pdf':
            return self._image_processor.convert_pdf_to_images(file_path, dpi=dpi)
        elif extension in ['.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls']:
            return self._image_processor.convert_office_document_to_images(file_path, extension, dpi=dpi)
        else:
            return self._image_processor.convert_document_to_images_basic(file_path)