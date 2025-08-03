from abc import ABC, abstractmethod
from ..models.conversion_request import ConversionRequest, AIConversionRequest
from ..models.conversion_result import ConversionResult, AIConversionResult


class FileConverterService(ABC):
    
    @abstractmethod
    def convert_file(self, request: ConversionRequest) -> ConversionResult:
        pass
    
    @abstractmethod
    def convert_image_with_ai(self, request: AIConversionRequest) -> ConversionResult:
        pass
    
    @abstractmethod
    def convert_document_with_ai(self, request: AIConversionRequest) -> AIConversionResult:
        pass