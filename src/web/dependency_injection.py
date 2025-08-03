from ..features.file_conversion.application.use_cases.convert_file import ConvertFileUseCase
from ..features.image_conversion.application.use_cases.convert_image import ConvertImageUseCase
from ..features.ai_conversion.application.use_cases.convert_with_ai import ConvertWithAIUseCase
from ..features.file_conversion.domain.services.markdown_enhancer import MarkdownEnhancerService
from ..features.file_conversion.infrastructure.adapters.markitdown_adapter import MarkItDownAdapter, MarkItDownLLMAdapter
from ..features.image_conversion.infrastructure.adapters.azure_openai_adapter import AzureOpenAIAdapter
from ..features.ai_conversion.infrastructure.adapters.image_converter_adapter import ImageConverterAdapter
from ..features.file_conversion.infrastructure.adapters.file_storage_adapter import FileStorageAdapter


class DependencyContainer:
    
    def __init__(self):
        self._markdown_enhancer = MarkdownEnhancerService()
        self._markitdown_adapter = MarkItDownAdapter()
        self._markitdown_llm_adapter = MarkItDownLLMAdapter()
        self._azure_openai_adapter = AzureOpenAIAdapter()
        self._image_converter_adapter = ImageConverterAdapter()
        self._file_storage_adapter = FileStorageAdapter()
        
        self._convert_file_use_case = ConvertFileUseCase(
            self._markitdown_adapter,
            self._file_storage_adapter,
            self._markdown_enhancer
        )
        
        self._convert_image_use_case = ConvertImageUseCase(
            self._markitdown_llm_adapter,
            self._azure_openai_adapter,
            self._file_storage_adapter,
            self._markdown_enhancer
        )
        
        self._convert_with_ai_use_case = ConvertWithAIUseCase(
            self._azure_openai_adapter,
            self._image_converter_adapter,
            self._file_storage_adapter,
            self._markdown_enhancer
        )
    
    @property
    def convert_file_use_case(self) -> ConvertFileUseCase:
        return self._convert_file_use_case
    
    @property
    def convert_image_use_case(self) -> ConvertImageUseCase:
        return self._convert_image_use_case
    
    @property
    def convert_with_ai_use_case(self) -> ConvertWithAIUseCase:
        return self._convert_with_ai_use_case
    
    @property
    def file_storage_adapter(self) -> FileStorageAdapter:
        return self._file_storage_adapter