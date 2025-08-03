from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class ConversionResult:
    success: bool
    markdown: str
    original_markdown: Optional[str] = None
    title: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class AIAnalysisResult:
    page: int
    status: str
    content_length: Optional[int] = None
    error: Optional[str] = None


@dataclass
class AIConversionResult(ConversionResult):
    analysis_results: List[AIAnalysisResult] = None
    pages_processed: int = 0
    successful_pages: int = 0
    failed_pages: int = 0