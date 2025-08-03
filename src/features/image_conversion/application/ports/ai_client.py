from abc import ABC, abstractmethod
from typing import Any


class AIClientPort(ABC):
    
    @abstractmethod
    def create_client(self, endpoint: str, api_key: str, api_version: str) -> Any:
        pass
    
    @abstractmethod
    def analyze_image(self, image_bytes: bytes, client: Any, deployment_name: str, page_num: int = None) -> str:
        pass