from abc import ABC, abstractmethod
from typing import List


class ImageProcessorPort(ABC):
    
    @abstractmethod
    def convert_pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[bytes]:
        pass
    
    @abstractmethod
    def convert_office_to_pdf(self, file_path: str, file_extension: str) -> str:
        pass
    
    @abstractmethod
    def convert_office_document_to_images(self, file_path: str, file_extension: str, dpi: int = 200) -> List[bytes]:
        pass
    
    @abstractmethod
    def convert_document_to_images_basic(self, file_path: str) -> List[bytes]:
        pass