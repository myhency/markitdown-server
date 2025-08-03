from dataclasses import dataclass
from typing import Optional


@dataclass
class FileInfo:
    filename: str
    extension: str
    mimetype: Optional[str]
    supported: bool
    
    @property
    def is_image(self) -> bool:
        return self.extension.lower() in {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
        }
    
    @property
    def is_ai_convertible(self) -> bool:
        return self.extension.lower() in {
            '.pdf', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'
        }