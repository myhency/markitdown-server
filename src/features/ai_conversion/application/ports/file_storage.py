from abc import ABC, abstractmethod
import tempfile
from typing import BinaryIO


class FileStoragePort(ABC):
    
    @abstractmethod
    def create_temp_file(self, suffix: str, prefix: str = 'markitdown_') -> tempfile.NamedTemporaryFile:
        pass
    
    @abstractmethod
    def save_uploaded_file(self, file: BinaryIO, temp_file_path: str) -> None:
        pass
    
    @abstractmethod
    def cleanup_temp_file(self, file_path: str) -> None:
        pass