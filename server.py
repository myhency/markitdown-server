from flask import Flask, request, jsonify, Response
import os
import tempfile
from werkzeug.utils import secure_filename
from markitdown import MarkItDown
import logging
from typing import Optional, List
import mimetypes
import json
import re
import base64
from io import BytesIO

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 한글 인코딩 문제 해결

# 업로드 파일 크기 제한 (100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# MarkItDown 인스턴스 생성
md_converter = MarkItDown(enable_plugins=False)

# 지원되는 파일 확장자
SUPPORTED_EXTENSIONS = {
    # Office 문서
    '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
    # PDF
    '.pdf',
    # 이미지
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    # 오디오
    '.wav', '.mp3',
    # 텍스트 기반
    '.txt', '.csv', '.json', '.xml', '.html', '.htm',
    # 아카이브
    '.zip',
    # 전자책
    '.epub',
    # Outlook
    '.msg'
}

# 이미지 파일 확장자 (LLM 처리용)
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
}

# AI 변환 지원 파일 (페이지별 이미지 변환 가능)
AI_CONVERTIBLE_EXTENSIONS = {
    '.pdf', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'
}

def is_image_file(filename: str) -> bool:
    """이미지 파일인지 확인"""
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)

def is_ai_convertible_file(filename: str) -> bool:
    """AI 변환 가능한 파일인지 확인"""
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in AI_CONVERTIBLE_EXTENSIONS)

def create_azure_openai_client(endpoint: str, api_key: str, api_version: str = "2024-02-01"):
    """Azure OpenAI 클라이언트 생성"""
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        return client
    except ImportError:
        raise ImportError("openai package is required for LLM features. Install with: pip install openai")
    except Exception as e:
        raise Exception(f"Failed to create Azure OpenAI client: {str(e)}")

def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[bytes]:
    """PDF를 페이지별 이미지로 변환"""
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        
        # PDF를 이미지로 변환
        images = convert_from_path(pdf_path, dpi=dpi)
        
        # 이미지를 바이트로 변환
        image_bytes_list = []
        for i, image in enumerate(images):
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_bytes_list.append(img_byte_arr.getvalue())
            logger.info(f"Converted page {i+1} to image")
        
        return image_bytes_list
    
    except ImportError:
        raise ImportError("pdf2image package is required. Install with: pip install pdf2image")
    except Exception as e:
        raise Exception(f"Failed to convert PDF to images: {str(e)}")

def convert_office_to_pdf(file_path: str, file_extension: str) -> str:
    """Office 문서를 PDF로 변환"""
    try:
        import tempfile
        import subprocess
        import shutil
        
        # 임시 디렉토리 생성
        temp_dir = tempfile.mkdtemp()
        try:
            # LibreOffice로 PDF 변환
            cmd = [
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', temp_dir, file_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"LibreOffice PDF conversion output: {result.stdout}")
            
            # 생성된 PDF 파일 찾기
            pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
            
            if not pdf_files:
                raise Exception(f"No PDF file generated in {temp_dir}")
            
            # 첫 번째 PDF 파일의 경로 반환
            pdf_path = os.path.join(temp_dir, pdf_files[0])
            logger.info(f"Successfully converted {file_extension} to PDF: {pdf_path}")
            
            return pdf_path
        
        except subprocess.CalledProcessError as e:
            logger.error(f"LibreOffice PDF conversion failed: {e.stderr}")
            raise Exception(f"Failed to convert {file_extension} to PDF: {e.stderr}")
            
    except Exception as e:
        logger.error(f"Office to PDF conversion error: {str(e)}")
        raise Exception(f"Failed to convert {file_extension} to PDF: {str(e)}")

def convert_office_document_to_images(file_path: str, file_extension: str, dpi: int = 200) -> List[bytes]:
    """Office 문서를 PDF를 거쳐 이미지로 변환 (통합 방식)"""
    temp_pdf_path = None
    temp_dir = None
    
    try:
        # 1단계: Office 문서를 PDF로 변환
        logger.info(f"Converting {file_extension} to PDF first...")
        temp_pdf_path = convert_office_to_pdf(file_path, file_extension)
        temp_dir = os.path.dirname(temp_pdf_path)
        
        # 2단계: PDF를 이미지로 변환
        logger.info(f"Converting PDF to images with DPI {dpi}...")
        image_bytes_list = convert_pdf_to_images(temp_pdf_path, dpi=dpi)
        
        logger.info(f"Successfully converted {file_extension} → PDF → {len(image_bytes_list)} images")
        return image_bytes_list
        
    except Exception as e:
        logger.error(f"Office document conversion failed: {str(e)}")
        # 실패 시 기본 방식으로 fallback
        logger.info("Falling back to basic image generation...")
        return convert_document_to_images_basic(file_path)
        
    finally:
        # 임시 파일 정리
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Could not clean up temporary directory {temp_dir}: {e}")

def convert_document_to_images_basic(file_path: str) -> List[bytes]:
    """기본 문서 → 이미지 변환 (fallback)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 간단한 플레이스홀더 이미지 생성
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"Document: {os.path.basename(file_path)}\nConverted to image placeholder"
        draw.text((50, 50), text, fill='black', font=font)
        
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        return [img_byte_arr.getvalue()]
    
    except Exception as e:
        raise Exception(f"Failed basic image conversion: {str(e)}")

def analyze_image_with_azure_openai(image_bytes: bytes, azure_client, deployment_name: str, page_num: int = None) -> str:
    """이미지를 Azure OpenAI로 분석"""
    try:
        # 이미지를 base64로 인코딩
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Azure OpenAI API 호출
        page_info = f"Page {page_num}" if page_num is not None else "Image"
        
        response = azure_client.chat.completions.create(
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

def enhance_markdown_structure(text: str, filename: str) -> str:
    """텍스트를 더 나은 마크다운 구조로 변환"""
    if not text or not text.strip():
        return text
    
    lines = text.split('\n')
    enhanced_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 빈 줄은 그대로 유지
        if not line:
            enhanced_lines.append('')
            continue
            
        # 이메일 주소가 있는 줄 처리
        if '<' in line and '@' in line and '>' in line:
            # 이메일을 마크다운 링크 형식으로 변환
            email_pattern = r'<([^@]+@[^>]+)>'
            line = re.sub(email_pattern, r'[\1](mailto:\1)', line)
            enhanced_lines.append(line)
            continue
        
        # 제목으로 보이는 줄 (첫 번째 줄이거나 길고 중요해 보이는 내용)
        if (i == 0 and len(line) > 10) or any(keyword in line for keyword in ['확인서', '증명서', '참가', 'Conference', 'Certificate']):
            enhanced_lines.append(f'# {line}')
            enhanced_lines.append('')  # 제목 다음에 빈 줄
            continue
            
        # 날짜 형식 감지
        if re.search(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', line) or re.search(r'\d{1,2}월\s*\d{1,2}일', line):
            enhanced_lines.append(f'**{line}**')
            continue
            
        # 콜론이 있는 줄 (항목: 값 형식)
        if ':' in line and len(line.split(':')) == 2:
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip()
            enhanced_lines.append(f'**{key}**: {value}')
            continue
            
        # 이름이나 중요 정보로 보이는 짧은 줄
        if len(line) < 20 and any(keyword in line for keyword in ['성명', '이름', '날짜', '시간', '장소']):
            enhanced_lines.append(f'**{line}**')
            continue
            
        # 일반 텍스트
        enhanced_lines.append(line)
    
    # 연속된 빈 줄 제거
    result_lines = []
    prev_empty = False
    
    for line in enhanced_lines:
        is_empty = not line.strip()
        if not (is_empty and prev_empty):
            result_lines.append(line)
        prev_empty = is_empty
    
    return '\n'.join(result_lines)

def is_allowed_file(filename: str) -> bool:
    """파일 확장자가 지원되는지 확인"""
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)

def get_file_info(filename: str) -> dict:
    """파일 정보 반환"""
    mimetype, _ = mimetypes.guess_type(filename)
    extension = os.path.splitext(filename.lower())[1]
    return {
        'filename': filename,
        'extension': extension,
        'mimetype': mimetype,
        'supported': is_allowed_file(filename)
    }

@app.route('/', methods=['GET'])
def home():
    """서버 상태 및 사용법 안내"""
    response_data = {
        'status': 'MarkItDown File Converter Server',
        'version': '1.0.0',
        'supported_formats': list(SUPPORTED_EXTENSIONS),
        'endpoints': {
            'convert': {
                'method': 'POST',
                'url': '/convert',
                'description': 'Upload a file to convert to Markdown',
                'parameters': {
                    'file': 'File to upload (required)',
                    'format': 'Response format: "json" or "text" (default: "json")',
                    'enhance_markdown': 'Enhance markdown structure: "true" or "false" (default: "true")'
                }
            },
            'convert_image': {
                'method': 'POST',
                'url': '/convert_image',
                'description': 'Convert image to Markdown with AI-powered description',
                'parameters': {
                    'file': 'Image file to upload (required)',
                    'azure_endpoint': 'Azure OpenAI endpoint URL (required)',
                    'api_key': 'Azure OpenAI API key (required)',
                    'deployment_name': 'Azure OpenAI deployment name (required)',
                    'api_version': 'Azure OpenAI API version (default: "2024-02-01")',
                    'format': 'Response format: "json" or "text" (default: "json")',
                    'enhance_markdown': 'Enhance markdown structure: "true" or "false" (default: "true")'
                }
            },
            'convert_with_ai': {
                'method': 'POST',
                'url': '/convert_with_ai',
                'description': 'Convert document to images and analyze with AI',
                'parameters': {
                    'file': 'Document file to upload (required)',
                    'azure_endpoint': 'Azure OpenAI endpoint URL (required)',
                    'api_key': 'Azure OpenAI API key (required)',
                    'deployment_name': 'Azure OpenAI deployment name (required)',
                    'api_version': 'Azure OpenAI API version (default: "2024-02-01")',
                    'dpi': 'DPI for PDF conversion (default: 200)',
                    'format': 'Response format: "json" or "text" (default: "json")',
                    'enhance_markdown': 'Enhance markdown structure: "true" or "false" (default: "true")'
                }
            },
            'health': {
                'method': 'GET',
                'url': '/health',
                'description': 'Server health check'
            }
        }
    }
    return Response(
        json.dumps(response_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8'
    )

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    response_data = {'status': 'healthy', 'service': 'markitdown-server'}
    return Response(
        json.dumps(response_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8'
    )

@app.route('/convert', methods=['POST'])
def convert_file():
    """파일을 Markdown으로 변환"""
    try:
        # 파일이 요청에 포함되어 있는지 확인
        if 'file' not in request.files:
            error_data = {
                'error': 'No file provided',
                'message': 'Please upload a file using the "file" field'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        file = request.files['file']
        
        # 파일이 선택되었는지 확인
        if file.filename == '':
            error_data = {
                'error': 'No file selected',
                'message': 'Please select a file to upload'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 응답 형식 확인 (기본값: json)
        response_format = request.form.get('format', 'json').lower()
        if response_format not in ['json', 'text']:
            error_data = {
                'error': 'Invalid format',
                'message': 'Format must be either "json" or "text"'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )
        
        # 후처리 옵션 확인
        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        # 파일 정보 가져오기
        file_info = get_file_info(file.filename)
        
        # 지원되는 파일 형식인지 확인
        if not file_info['supported']:
            error_data = {
                'error': 'Unsupported file format',
                'message': f'File extension {file_info["extension"]} is not supported',
                'supported_formats': list(SUPPORTED_EXTENSIONS),
                'file_info': file_info
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 임시 파일로 저장하여 변환 수행
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_info['extension'],
            prefix='markitdown_'
        ) as temp_file:
            try:
                # 파일 내용을 임시 파일에 저장
                file.save(temp_file.name)
                temp_file.flush()
                
                logger.info(f"Converting file: {file.filename} (temp: {temp_file.name})")
                
                # MarkItDown으로 변환
                result = md_converter.convert(temp_file.name)
                
                # 변환 결과 확인
                if not result or not result.text_content:
                    error_data = {
                        'error': 'Conversion failed',
                        'message': 'The file could not be converted to Markdown',
                        'file_info': file_info
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )

                # 마크다운 후처리
                markdown_content = result.text_content
                if enhance_markdown:
                    markdown_content = enhance_markdown_structure(markdown_content, file.filename)

                logger.info(f"Successfully converted {file.filename}")
                
                # 응답 형식에 따라 반환
                if response_format == 'text':
                    return Response(
                        markdown_content,
                        mimetype='text/markdown; charset=utf-8',
                        headers={
                            'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}.md"'
                        }
                    )
                else:
                    response_data = {
                        'success': True,
                        'markdown': markdown_content,
                        'original_markdown': result.text_content,  # 원본도 포함
                        'file_info': file_info,
                        'processing_info': {
                            'enhanced': enhance_markdown
                        },
                        'metadata': {
                            'original_filename': file.filename,
                            'converted_size': len(markdown_content),
                            'original_size': len(result.text_content),
                            'title': getattr(result, 'title', None)
                        }
                    }
                    # 한글이 제대로 표시되도록 ensure_ascii=False 설정
                    return Response(
                        json.dumps(response_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8'
                    )
                    
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    logger.warning(f"Could not delete temporary file: {temp_file.name}")

    except Exception as e:
        logger.error(f"Error converting file: {str(e)}")
        error_data = {
            'error': 'Internal server error',
            'message': str(e)
        }
        return Response(
            json.dumps(error_data, ensure_ascii=False, indent=2),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.route('/convert_image', methods=['POST'])
def convert_image_with_llm():
    """이미지를 LLM을 사용해서 Markdown으로 변환"""
    try:
        # 파일이 요청에 포함되어 있는지 확인
        if 'file' not in request.files:
            error_data = {
                'error': 'No file provided',
                'message': 'Please upload an image file using the "file" field'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        file = request.files['file']
        
        # 파일이 선택되었는지 확인
        if file.filename == '':
            error_data = {
                'error': 'No file selected',
                'message': 'Please select an image file to upload'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 이미지 파일인지 확인
        if not is_image_file(file.filename):
            error_data = {
                'error': 'Not an image file',
                'message': f'File must be an image. Supported formats: {", ".join(IMAGE_EXTENSIONS)}',
                'supported_image_formats': list(IMAGE_EXTENSIONS)
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # Azure OpenAI 설정 확인
        azure_endpoint = request.form.get('azure_endpoint', '').strip()
        api_key = request.form.get('api_key', '').strip()
        deployment_name = request.form.get('deployment_name', '').strip()
        api_version = request.form.get('api_version', '2024-02-01').strip()

        if not azure_endpoint or not api_key or not deployment_name:
            error_data = {
                'error': 'Missing Azure OpenAI configuration',
                'message': 'azure_endpoint, api_key, and deployment_name are required',
                'required_fields': ['azure_endpoint', 'api_key', 'deployment_name']
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 응답 형식 확인
        response_format = request.form.get('format', 'json').lower()
        if response_format not in ['json', 'text']:
            error_data = {
                'error': 'Invalid format',
                'message': 'Format must be either "json" or "text"'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 후처리 옵션 확인
        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        # 파일 정보 가져오기
        file_info = get_file_info(file.filename)

        # 임시 파일로 저장하여 변환 수행
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_info['extension'],
            prefix='markitdown_image_'
        ) as temp_file:
            try:
                # 파일 내용을 임시 파일에 저장
                file.save(temp_file.name)
                temp_file.flush()
                
                logger.info(f"Converting image with LLM: {file.filename} (temp: {temp_file.name})")
                
                # Azure OpenAI 클라이언트 생성
                try:
                    azure_client = create_azure_openai_client(azure_endpoint, api_key, api_version)
                except Exception as e:
                    error_data = {
                        'error': 'Azure OpenAI client error',
                        'message': str(e)
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )
                
                # LLM 기능이 있는 MarkItDown 인스턴스 생성
                try:
                    llm_converter = MarkItDown(
                        llm_client=azure_client,
                        llm_model=deployment_name
                    )
                except Exception as e:
                    error_data = {
                        'error': 'MarkItDown LLM initialization error',
                        'message': str(e)
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )
                
                # 이미지를 LLM으로 변환
                try:
                    result = llm_converter.convert(temp_file.name)
                except Exception as e:
                    error_data = {
                        'error': 'LLM conversion failed',
                        'message': f'Failed to convert image with LLM: {str(e)}'
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )
                
                # 변환 결과 확인
                if not result or not result.text_content:
                    error_data = {
                        'error': 'Conversion failed',
                        'message': 'The image could not be converted to Markdown with LLM',
                        'file_info': file_info
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )

                # 마크다운 후처리
                markdown_content = result.text_content
                if enhance_markdown:
                    markdown_content = enhance_markdown_structure(markdown_content, file.filename)

                logger.info(f"Successfully converted image with LLM: {file.filename}")
                
                # 응답 형식에 따라 반환
                if response_format == 'text':
                    return Response(
                        markdown_content,
                        mimetype='text/markdown; charset=utf-8',
                        headers={
                            'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}_llm.md"'
                        }
                    )
                else:
                    response_data = {
                        'success': True,
                        'markdown': markdown_content,
                        'original_markdown': result.text_content,
                        'file_info': file_info,
                        'processing_info': {
                            'llm_used': True,
                            'llm_model': deployment_name,
                            'azure_endpoint': azure_endpoint,
                            'enhanced': enhance_markdown
                        },
                        'metadata': {
                            'original_filename': file.filename,
                            'converted_size': len(markdown_content),
                            'original_size': len(result.text_content),
                            'title': getattr(result, 'title', None)
                        }
                    }
                    return Response(
                        json.dumps(response_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8'
                    )
                    
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    logger.warning(f"Could not delete temporary file: {temp_file.name}")

    except Exception as e:
        logger.error(f"Error converting image with LLM: {str(e)}")
        error_data = {
            'error': 'Internal server error',
            'message': str(e)
        }
        return Response(
            json.dumps(error_data, ensure_ascii=False, indent=2),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.route('/convert_with_ai', methods=['POST'])
def convert_document_with_ai():
    """문서를 이미지로 변환한 후 AI로 분석"""
    try:
        # 파일이 요청에 포함되어 있는지 확인
        if 'file' not in request.files:
            error_data = {
                'error': 'No file provided',
                'message': 'Please upload a document file using the "file" field'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        file = request.files['file']
        
        # 파일이 선택되었는지 확인
        if file.filename == '':
            error_data = {
                'error': 'No file selected',
                'message': 'Please select a document file to upload'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # AI 변환 가능한 파일인지 확인
        if not is_ai_convertible_file(file.filename):
            error_data = {
                'error': 'File not supported for AI conversion',
                'message': f'File must be convertible to images. Supported formats: {", ".join(AI_CONVERTIBLE_EXTENSIONS)}',
                'supported_ai_formats': list(AI_CONVERTIBLE_EXTENSIONS)
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # Azure OpenAI 설정 확인
        azure_endpoint = request.form.get('azure_endpoint', '').strip()
        api_key = request.form.get('api_key', '').strip()
        deployment_name = request.form.get('deployment_name', '').strip()
        api_version = request.form.get('api_version', '2024-02-01').strip()

        if not azure_endpoint or not api_key or not deployment_name:
            error_data = {
                'error': 'Missing Azure OpenAI configuration',
                'message': 'azure_endpoint, api_key, and deployment_name are required',
                'required_fields': ['azure_endpoint', 'api_key', 'deployment_name']
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 기타 옵션
        dpi = int(request.form.get('dpi', 200))
        response_format = request.form.get('format', 'json').lower()
        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        if response_format not in ['json', 'text']:
            error_data = {
                'error': 'Invalid format',
                'message': 'Format must be either "json" or "text"'
            }
            return Response(
                json.dumps(error_data, ensure_ascii=False, indent=2),
                mimetype='application/json; charset=utf-8',
                status=400
            )

        # 파일 정보 가져오기
        file_info = get_file_info(file.filename)

        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_info['extension'],
            prefix='markitdown_ai_'
        ) as temp_file:
            try:
                # 파일 내용을 임시 파일에 저장
                file.save(temp_file.name)
                temp_file.flush()
                
                logger.info(f"Converting document with AI: {file.filename} (temp: {temp_file.name})")
                
                # Azure OpenAI 클라이언트 생성
                try:
                    azure_client = create_azure_openai_client(azure_endpoint, api_key, api_version)
                except Exception as e:
                    error_data = {
                        'error': 'Azure OpenAI client error',
                        'message': str(e)
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )
                
                # 문서를 이미지로 변환
                try:
                    extension = file_info['extension'].lower()
                    if extension == '.pdf':
                        # PDF는 직접 이미지로 변환
                        image_bytes_list = convert_pdf_to_images(temp_file.name, dpi=dpi)
                    elif extension in ['.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls']:
                        # Office 파일들: PDF를 거쳐 이미지로 변환
                        image_bytes_list = convert_office_document_to_images(temp_file.name, extension, dpi=dpi)
                    else:
                        # 기타 파일: 기본 방식
                        image_bytes_list = convert_document_to_images_basic(temp_file.name)
                    
                    logger.info(f"Converted {len(image_bytes_list)} pages/slides/sheets to images")
                
                except Exception as e:
                    error_data = {
                        'error': 'Document to image conversion failed',
                        'message': f'Failed to convert document to images: {str(e)}'
                    }
                    return Response(
                        json.dumps(error_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8',
                        status=500
                    )
                
                # 각 이미지를 AI로 분석
                markdown_pages = []
                analysis_results = []
                
                for i, image_bytes in enumerate(image_bytes_list):
                    try:
                        page_markdown = analyze_image_with_azure_openai(
                            image_bytes, azure_client, deployment_name, i + 1
                        )
                        markdown_pages.append(page_markdown)
                        analysis_results.append({
                            'page': i + 1,
                            'status': 'success',
                            'content_length': len(page_markdown)
                        })
                        logger.info(f"Successfully analyzed page {i + 1}")
                    
                    except Exception as e:
                        error_markdown = f"# Page {i + 1}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
                        markdown_pages.append(error_markdown)
                        analysis_results.append({
                            'page': i + 1,
                            'status': 'error',
                            'error': str(e)
                        })
                        logger.error(f"Failed to analyze page {i + 1}: {str(e)}")
                
                # 모든 페이지를 하나의 마크다운으로 통합
                combined_markdown = "\n\n---\n\n".join(markdown_pages)
                
                # 마크다운 후처리
                if enhance_markdown:
                    combined_markdown = enhance_markdown_structure(combined_markdown, file.filename)

                logger.info(f"Successfully converted {file.filename} with AI analysis")
                
                # 응답 형식에 따라 반환
                if response_format == 'text':
                    return Response(
                        combined_markdown,
                        mimetype='text/markdown; charset=utf-8',
                        headers={
                            'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}_ai_analyzed.md"'
                        }
                    )
                else:
                    response_data = {
                        'success': True,
                        'markdown': combined_markdown,
                        'file_info': file_info,
                        'processing_info': {
                            'method': 'ai_image_analysis',
                            'llm_used': True,
                            'llm_model': deployment_name,
                            'azure_endpoint': azure_endpoint,
                            'enhanced': enhance_markdown,
                            'total_pages': len(image_bytes_list),
                            'dpi': dpi if extension == '.pdf' else None
                        },
                        'analysis_results': analysis_results,
                        'metadata': {
                            'original_filename': file.filename,
                            'converted_size': len(combined_markdown),
                            'pages_processed': len(image_bytes_list),
                            'successful_pages': len([r for r in analysis_results if r['status'] == 'success']),
                            'failed_pages': len([r for r in analysis_results if r['status'] == 'error'])
                        }
                    }
                    return Response(
                        json.dumps(response_data, ensure_ascii=False, indent=2),
                        mimetype='application/json; charset=utf-8'
                    )
                    
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    logger.warning(f"Could not delete temporary file: {temp_file.name}")

    except Exception as e:
        logger.error(f"Error converting document with AI: {str(e)}")
        error_data = {
            'error': 'Internal server error',
            'message': str(e)
        }
        return Response(
            json.dumps(error_data, ensure_ascii=False, indent=2),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.errorhandler(413)
def too_large(e):
    """파일 크기 초과 에러 처리"""
    error_data = {
        'error': 'File too large',
        'message': 'File size exceeds the maximum limit of 100MB'
    }
    return Response(
        json.dumps(error_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=413
    )

@app.errorhandler(404)
def not_found(e):
    """404 에러 처리"""
    error_data = {
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': ['/convert', '/convert_image', '/convert_with_ai', '/health', '/']
    }
    return Response(
        json.dumps(error_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=404
    )

@app.errorhandler(405)
def method_not_allowed(e):
    """메서드 허용되지 않음 에러 처리"""
    error_data = {
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }
    return Response(
        json.dumps(error_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=405
    )

if __name__ == '__main__':
    # 개발 서버 실행
    print("🚀 MarkItDown File Converter Server Starting...")
    print("📁 Supported file formats:", ', '.join(sorted(SUPPORTED_EXTENSIONS)))
    print("🖼️  AI convertible formats:", ', '.join(sorted(AI_CONVERTIBLE_EXTENSIONS)))
    print("   - PDF: Direct page-by-page conversion")
    print("   - Office files: Convert to PDF first, then to images") 
    print("   - PowerPoint/Word/Excel: [File] → PDF → Images → AI Analysis")
    print("🌐 Server will be available at: http://localhost:5001")
    print("📖 API documentation: http://localhost:5001")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        use_reloader=True
    )