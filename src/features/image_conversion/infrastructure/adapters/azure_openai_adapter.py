import base64
import logging
import mimetypes
from typing import Any, Iterator
from ...application.ports.ai_client import AIClientPort
from ...application.ports.conversion_engine import LLMConversionEnginePort
from ...domain.exceptions.conversion_exceptions import AIClientException

logger = logging.getLogger(__name__)


class AzureOpenAIAdapter(AIClientPort, LLMConversionEnginePort):
    
    def create_client(self, endpoint: str, api_key: str, api_version: str) -> Any:
        try:
            from openai import AzureOpenAI
            
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            return client
        except ImportError:
            raise AIClientException("openai package is required for LLM features. Install with: pip install openai")
        except Exception as e:
            raise AIClientException(f"Failed to create Azure OpenAI client: {str(e)}")
    
    def analyze_image(self, image_bytes: bytes, client: Any, deployment_name: str, page_num: int = None, file_path: str = None) -> str:
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Detect image MIME type
            if file_path:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type or not mime_type.startswith('image/'):
                    mime_type = 'image/png'  # fallback
            else:
                mime_type = 'image/png'  # fallback
            
            page_info = f"Page {page_num}" if page_num is not None else "Image"
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing images and converting visual content to markdown format. You have full vision capabilities and can see and analyze images perfectly."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""You MUST analyze the image I'm providing. Do not refuse or say you cannot see images.

Please carefully examine this {page_info.lower()} and:

1. Extract ALL visible text exactly as it appears
2. Describe visual elements, charts, diagrams, or illustrations in detail
3. Maintain document structure (headings, lists, tables, etc.)
4. Convert everything to proper markdown format

Required markdown syntax:
- # for main headings
- ## for subheadings  
- **bold** for emphasis
- - for bullet points
- | col1 | col2 | for tables
- [Image: detailed description] for visual elements

Output requirements:
- Start with a clear heading
- Use Korean if content is Korean, otherwise use the original language
- Include both text content AND visual descriptions
- Format as clean, well-structured markdown

Begin your analysis now:"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                stream=False,
                temperature=0.1
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Azure OpenAI analysis failed for {page_info}: {str(e)}")
            return f"# {page_info}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
    
    def analyze_image_stream(self, image_bytes: bytes, client: Any, deployment_name: str, page_num: int = None, file_path: str = None) -> Iterator[str]:
        """Stream-enabled image analysis"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Detect image MIME type
            if file_path:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type or not mime_type.startswith('image/'):
                    mime_type = 'image/png'  # fallback
            else:
                mime_type = 'image/png'  # fallback
            
            page_info = f"Page {page_num}" if page_num is not None else "Image"
            
            # Debug logging
            logger.info(f"Image analysis - Size: {len(image_bytes)} bytes, MIME: {mime_type}, Base64 length: {len(image_base64)}")
            logger.info(f"Using deployment: {deployment_name}")
            logger.info(f"Image URL format: data:{mime_type};base64,[{len(image_base64)} chars]")
            logger.info(f"Base64 sample: {image_base64[:50]}...")
            
            # Check if model supports vision
            if 'gpt-4' not in deployment_name.lower() and 'vision' not in deployment_name.lower():
                logger.warning(f"Model {deployment_name} may not support vision. Consider using gpt-4-vision-preview or gpt-4o")
            
            logger.info(f"Making API call to Azure OpenAI with model: {deployment_name}")
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing images and converting visual content to markdown format. You have full vision capabilities and can see and analyze images perfectly."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""You MUST analyze the image I'm providing. Do not refuse or say you cannot see images.

Please carefully examine this {page_info.lower()} and:

1. Extract ALL visible text exactly as it appears
2. Describe visual elements, charts, diagrams, or illustrations in detail
3. Maintain document structure (headings, lists, tables, etc.)
4. Convert everything to proper markdown format

Required markdown syntax:
- # for main headings
- ## for subheadings  
- **bold** for emphasis
- - for bullet points
- | col1 | col2 | for tables
- [Image: detailed description] for visual elements

Output requirements:
- Start with a clear heading
- Use Korean if content is Korean, otherwise use the original language
- Include both text content AND visual descriptions
- Format as clean, well-structured markdown

Begin your analysis now:"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                stream=True,
                temperature=0.1
            )
            
            # Yield streaming chunks
            for chunk in response:
                try:
                    # Safely extract content from chunk
                    if chunk and chunk.choices:
                        choice = chunk.choices[0] if len(chunk.choices) > 0 else None
                        if choice and choice.delta and choice.delta.content:
                            yield choice.delta.content
                except (IndexError, AttributeError) as chunk_error:
                    logger.debug(f"Skipping chunk due to: {str(chunk_error)}")
                    continue
                except Exception as chunk_error:
                    logger.error(f"Unexpected error processing chunk: {str(chunk_error)}")
                    continue
            
        except Exception as e:
            logger.error(f"Azure OpenAI streaming analysis failed for {page_info}: {str(e)}")
            yield f"# {page_info}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
    
    def convert_with_llm(self, file_path: str, llm_client: Any, llm_model: str) -> Any:
        try:
            # Read image file
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            
            # Analyze image using LLM
            markdown_content = self.analyze_image(image_bytes, llm_client, llm_model, file_path=file_path)
            
            # Return a simple object with text_content attribute (like MarkItDown does)
            class ImageAnalysisResult:
                def __init__(self, text_content):
                    self.text_content = text_content
                    self.title = None
            
            return ImageAnalysisResult(markdown_content)
            
        except Exception as e:
            logger.error(f"LLM conversion failed for {file_path}: {str(e)}")
            # Return an object that indicates failure
            class FailedResult:
                def __init__(self, error):
                    self.text_content = None
                    self.error = error
            
            return FailedResult(str(e))