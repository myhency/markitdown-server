import os
import tempfile
import logging
from typing import BinaryIO
from ...application.ports.file_storage import FileStoragePort

logger = logging.getLogger(__name__)


class FileStorageAdapter(FileStoragePort):
    
    def create_temp_file(self, suffix: str, prefix: str = 'markitdown_') -> tempfile.NamedTemporaryFile:
        return tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            prefix=prefix
        )
    
    def save_uploaded_file(self, file: BinaryIO, temp_file_path: str) -> None:
        file.save(temp_file_path)
    
    def cleanup_temp_file(self, file_path: str) -> None:
        try:
            os.unlink(file_path)
        except OSError:
            logger.warning(f"Could not delete temporary file: {file_path}")