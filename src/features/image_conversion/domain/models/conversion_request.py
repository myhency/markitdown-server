from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversionRequest:
    file_path: str
    filename: str
    enhance_markdown: bool = True
    

@dataclass
class AIConversionRequest:
    file_path: str
    filename: str
    azure_endpoint: str
    api_key: str
    deployment_name: str
    enhance_markdown: bool = True
    api_version: str = "2024-02-01"
    dpi: int = 200