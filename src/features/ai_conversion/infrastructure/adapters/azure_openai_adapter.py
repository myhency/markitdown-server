import base64
import logging
from typing import Any
from ...application.ports.ai_client import AIClientPort
from ...domain.exceptions.conversion_exceptions import AIClientException

logger = logging.getLogger(__name__)


class AzureOpenAIAdapter(AIClientPort):
    
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
    
    def analyze_image(self, image_bytes: bytes, client: Any, deployment_name: str, page_num: int = None) -> str:
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            page_info = f"Page {page_num}" if page_num is not None else "Image"
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Please analyze this {page_info.lower()} image and convert it to markdown format. 
                                
Extract all visible text, maintain the document structure (headings, lists, tables, etc.), 
and describe any important visual elements like charts, diagrams, or images.

Use proper markdown syntax:
- # for main headings
- ## for subheadings  
- **bold** for emphasis
- - for bullet points
- | | for tables
- Describe images/charts in [Image: description] format

Please provide a clean, well-structured markdown output in Korean if the content is in Korean, otherwise in the original language."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Azure OpenAI analysis failed for {page_info}: {str(e)}")
            return f"# {page_info}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
    
    def analyze_image_stream(self, image_bytes: bytes, client: Any, deployment_name: str, page_number: int = None):
        """Stream AI analysis of image with real-time response chunks"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            page_info = f"Page {page_number}" if page_number is not None else "Image"
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Please analyze this {page_info.lower()} image and convert it to markdown format. 
                                
Extract all visible text, maintain the document structure (headings, lists, tables, etc.), 
and describe any important visual elements like charts, diagrams, or images.

Use proper markdown syntax:
- # for main headings
- ## for subheadings  
- **bold** for emphasis
- - for bullet points
- | | for tables
- Describe images/charts in [Image: description] format

Please provide a clean, well-structured markdown output in Korean if the content is in Korean, otherwise in the original language."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Azure OpenAI streaming analysis failed for {page_info}: {str(e)}")
            yield f"# {page_info}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"