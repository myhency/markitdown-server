from abc import ABC, abstractmethod
from typing import Any


class ConversionEnginePort(ABC):
    
    @abstractmethod
    def convert(self, file_path: str) -> Any:
        pass


class LLMConversionEnginePort(ABC):
    
    @abstractmethod
    def convert_with_llm(self, file_path: str, llm_client: Any, llm_model: str) -> Any:
        pass