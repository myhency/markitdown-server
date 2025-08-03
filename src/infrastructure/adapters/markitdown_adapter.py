from markitdown import MarkItDown
from ...application.ports.conversion_engine import ConversionEnginePort, LLMConversionEnginePort
from typing import Any


class MarkItDownAdapter(ConversionEnginePort):
    
    def __init__(self):
        self._converter = MarkItDown(enable_plugins=False)
    
    def convert(self, file_path: str) -> Any:
        return self._converter.convert(file_path)


class MarkItDownLLMAdapter(LLMConversionEnginePort):
    
    def convert_with_llm(self, file_path: str, llm_client: Any, llm_model: str) -> Any:
        converter = MarkItDown(
            llm_client=llm_client,
            llm_model=llm_model
        )
        return converter.convert(file_path)