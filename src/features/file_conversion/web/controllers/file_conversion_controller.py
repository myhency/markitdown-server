import json
import os
from flask import Blueprint, request, Response, current_app, stream_with_context
from ...domain.models.conversion_request import ConversionRequest, AIConversionRequest
from .....shared.infrastructure.utils.file_utils import get_file_info, SUPPORTED_EXTENSIONS
from ...domain.exceptions.conversion_exceptions import UnsupportedFileFormatException


file_conversion_bp = Blueprint('file_conversion', __name__)

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
}

AI_CONVERTIBLE_EXTENSIONS = {
    '.pdf', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'
}


def create_sse_response(data, event_type="message"):
    """Create SSE formatted response"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@file_conversion_bp.route('/convert', methods=['POST'])
def convert_file():
    try:
        if 'file' not in request.files:
            return _error_response('No file provided', 'Please upload a file using the "file" field', 400)

        file = request.files['file']
        
        if file.filename == '':
            return _error_response('No file selected', 'Please select a file to upload', 400)

        response_format = request.form.get('format', 'json').lower()
        if response_format not in ['json', 'text']:
            return _error_response('Invalid format', 'Format must be either "json" or "text"', 400)
        
        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        file_info = get_file_info(file.filename)
        
        if not file_info.supported:
            return _error_response(
                'Unsupported file format', 
                f'File extension {file_info.extension} is not supported',
                400,
                {'supported_formats': list(SUPPORTED_EXTENSIONS), 'file_info': file_info.__dict__}
            )

        temp_file = current_app.container.file_storage_adapter.create_temp_file(
            suffix=file_info.extension,
            prefix='markitdown_'
        )
        
        try:
            current_app.container.file_storage_adapter.save_uploaded_file(file, temp_file.name)
            temp_file.flush()
            
            conversion_request = ConversionRequest(
                file_path=temp_file.name,
                filename=file.filename,
                enhance_markdown=enhance_markdown
            )
            
            result = current_app.container.convert_file_use_case.execute(conversion_request)
            
            if not result.success:
                return _error_response('Conversion failed', result.error_message, 500, {'file_info': file_info.__dict__})

            if response_format == 'text':
                return Response(
                    result.markdown,
                    mimetype='text/markdown; charset=utf-8',
                    headers={
                        'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}.md"'
                    }
                )
            else:
                response_data = {
                    'success': True,
                    'markdown': result.markdown,
                    'original_markdown': result.original_markdown,
                    'file_info': file_info.__dict__,
                    'processing_info': {
                        'enhanced': enhance_markdown
                    },
                    'metadata': result.metadata
                }
                return Response(
                    json.dumps(response_data, ensure_ascii=False, indent=2),
                    mimetype='application/json; charset=utf-8'
                )
                
        finally:
            current_app.container.file_storage_adapter.cleanup_temp_file(temp_file.name)

    except Exception as e:
        return _error_response('Internal server error', str(e), 500)


@file_conversion_bp.route('/convert_image', methods=['POST'])
def convert_image_with_llm():
    try:
        if 'file' not in request.files:
            return _error_response('No file provided', 'Please upload an image file using the "file" field', 400)

        file = request.files['file']
        
        if file.filename == '':
            return _error_response('No file selected', 'Please select an image file to upload', 400)

        file_info = get_file_info(file.filename)
        
        if not file_info.is_image:
            return _error_response(
                'Not an image file',
                f'File must be an image. Supported formats: {", ".join(IMAGE_EXTENSIONS)}',
                400,
                {'supported_image_formats': list(IMAGE_EXTENSIONS)}
            )

        azure_endpoint = request.form.get('azure_endpoint', '').strip()
        api_key = request.form.get('api_key', '').strip()
        deployment_name = request.form.get('deployment_name', '').strip()
        api_version = request.form.get('api_version', '2024-02-01').strip()

        if not azure_endpoint or not api_key or not deployment_name:
            return _error_response(
                'Missing Azure OpenAI configuration',
                'azure_endpoint, api_key, and deployment_name are required',
                400,
                {'required_fields': ['azure_endpoint', 'api_key', 'deployment_name']}
            )

        response_format = request.form.get('format', 'json').lower()
        if response_format not in ['json', 'text']:
            return _error_response('Invalid format', 'Format must be either "json" or "text"', 400)

        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        temp_file = current_app.container.file_storage_adapter.create_temp_file(
            suffix=file_info.extension,
            prefix='markitdown_image_'
        )
        
        try:
            current_app.container.file_storage_adapter.save_uploaded_file(file, temp_file.name)
            temp_file.flush()
            
            conversion_request = AIConversionRequest(
                file_path=temp_file.name,
                filename=file.filename,
                enhance_markdown=enhance_markdown,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                deployment_name=deployment_name,
                api_version=api_version
            )
            
            result = current_app.container.convert_image_use_case.execute(conversion_request)
            
            if not result.success:
                return _error_response('LLM conversion failed', result.error_message, 500)

            if response_format == 'text':
                return Response(
                    result.markdown,
                    mimetype='text/markdown; charset=utf-8',
                    headers={
                        'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}_llm.md"'
                    }
                )
            else:
                response_data = {
                    'success': True,
                    'markdown': result.markdown,
                    'original_markdown': result.original_markdown,
                    'file_info': file_info.__dict__,
                    'processing_info': result.metadata,
                    'metadata': {
                        'original_filename': file.filename,
                        'converted_size': len(result.markdown),
                        'title': result.title
                    }
                }
                return Response(
                    json.dumps(response_data, ensure_ascii=False, indent=2),
                    mimetype='application/json; charset=utf-8'
                )
                
        finally:
            current_app.container.file_storage_adapter.cleanup_temp_file(temp_file.name)

    except Exception as e:
        return _error_response('Internal server error', str(e), 500)


@file_conversion_bp.route('/convert_with_ai', methods=['POST'])
def convert_document_with_ai():
    try:
        if 'file' not in request.files:
            return _error_response('No file provided', 'Please upload a document file using the "file" field', 400)

        file = request.files['file']
        
        if file.filename == '':
            return _error_response('No file selected', 'Please select a document file to upload', 400)

        file_info = get_file_info(file.filename)
        
        if not file_info.is_ai_convertible:
            return _error_response(
                'File not supported for AI conversion',
                f'File must be convertible to images. Supported formats: {", ".join(AI_CONVERTIBLE_EXTENSIONS)}',
                400,
                {'supported_ai_formats': list(AI_CONVERTIBLE_EXTENSIONS)}
            )

        azure_endpoint = request.form.get('azure_endpoint', '').strip()
        api_key = request.form.get('api_key', '').strip()
        deployment_name = request.form.get('deployment_name', '').strip()
        api_version = request.form.get('api_version', '2024-02-01').strip()

        if not azure_endpoint or not api_key or not deployment_name:
            return _error_response(
                'Missing Azure OpenAI configuration',
                'azure_endpoint, api_key, and deployment_name are required',
                400,
                {'required_fields': ['azure_endpoint', 'api_key', 'deployment_name']}
            )

        dpi = int(request.form.get('dpi', 200))
        response_format = request.form.get('format', 'json').lower()
        enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

        if response_format not in ['json', 'text']:
            return _error_response('Invalid format', 'Format must be either "json" or "text"', 400)

        temp_file = current_app.container.file_storage_adapter.create_temp_file(
            suffix=file_info.extension,
            prefix='markitdown_ai_'
        )
        
        try:
            current_app.container.file_storage_adapter.save_uploaded_file(file, temp_file.name)
            temp_file.flush()
            
            conversion_request = AIConversionRequest(
                file_path=temp_file.name,
                filename=file.filename,
                enhance_markdown=enhance_markdown,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                deployment_name=deployment_name,
                api_version=api_version,
                dpi=dpi
            )
            
            result = current_app.container.convert_with_ai_use_case.execute(conversion_request)
            
            if not result.success:
                return _error_response('AI conversion failed', result.error_message, 500)

            if response_format == 'text':
                return Response(
                    result.markdown,
                    mimetype='text/markdown; charset=utf-8',
                    headers={
                        'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}_ai_analyzed.md"'
                    }
                )
            else:
                response_data = {
                    'success': True,
                    'markdown': result.markdown,
                    'file_info': file_info.__dict__,
                    'processing_info': result.metadata,
                    'analysis_results': [r.__dict__ for r in result.analysis_results],
                    'metadata': {
                        'original_filename': file.filename,
                        'converted_size': len(result.markdown),
                        'pages_processed': result.pages_processed,
                        'successful_pages': result.successful_pages,
                        'failed_pages': result.failed_pages
                    }
                }
                return Response(
                    json.dumps(response_data, ensure_ascii=False, indent=2),
                    mimetype='application/json; charset=utf-8'
                )
                
        finally:
            current_app.container.file_storage_adapter.cleanup_temp_file(temp_file.name)

    except Exception as e:
        return _error_response('Internal server error', str(e), 500)


@file_conversion_bp.route('/convert_with_ai/stream', methods=['POST'])
def convert_document_with_ai_stream():
    """Stream AI document conversion with SSE"""
    def generate():
        try:
            # Send initial connection event
            yield create_sse_response({
                "status": "connected",
                "message": "Connection established"
            }, "connection")

            # Validate file
            if 'file' not in request.files:
                yield create_sse_response({
                    "status": "error",
                    "message": "No file provided. Please upload a document file using the 'file' field"
                }, "error")
                return

            file = request.files['file']
            if file.filename == '':
                yield create_sse_response({
                    "status": "error", 
                    "message": "No file selected. Please select a document file to upload"
                }, "error")
                return

            file_info = get_file_info(file.filename)
            
            # Check if file is AI convertible
            if not file_info.is_ai_convertible:
                yield create_sse_response({
                    "status": "error",
                    "message": f"File not supported for AI conversion. Supported formats: {', '.join(AI_CONVERTIBLE_EXTENSIONS)}",
                    "supported_ai_formats": list(AI_CONVERTIBLE_EXTENSIONS)
                }, "error")
                return

            # Get request parameters
            azure_endpoint = request.form.get('azure_endpoint', '').strip()
            api_key = request.form.get('api_key', '').strip()
            deployment_name = request.form.get('deployment_name', '').strip()
            api_version = request.form.get('api_version', '2024-02-01').strip()
            dpi = int(request.form.get('dpi', 200))
            enhance_markdown = request.form.get('enhance_markdown', 'true').lower() == 'true'

            # Validate required parameters
            if not azure_endpoint or not api_key or not deployment_name:
                yield create_sse_response({
                    "status": "error",
                    "message": "Missing Azure OpenAI configuration",
                    "details": "azure_endpoint, api_key, and deployment_name are required",
                    "required_fields": ["azure_endpoint", "api_key", "deployment_name"]
                }, "error")
                return

            yield create_sse_response({
                "status": "processing",
                "message": "File uploaded successfully, starting AI conversion...",
                "filename": file.filename,
                "file_info": file_info.__dict__
            }, "progress")

            # Create temp file
            temp_file = current_app.container.file_storage_adapter.create_temp_file(
                suffix=file_info.extension,
                prefix='markitdown_ai_stream_'
            )
            
            try:
                current_app.container.file_storage_adapter.save_uploaded_file(file, temp_file.name)
                temp_file.flush()
                
                yield create_sse_response({
                    "status": "processing",
                    "message": "Initializing AI conversion process...",
                    "step": "ai_init"
                }, "progress")

                # Create conversion request
                conversion_request = AIConversionRequest(
                    file_path=temp_file.name,
                    filename=file.filename,
                    enhance_markdown=enhance_markdown,
                    azure_endpoint=azure_endpoint,
                    api_key=api_key,
                    deployment_name=deployment_name,
                    api_version=api_version,
                    dpi=dpi
                )
                
                # Create Azure AI client
                ai_client = current_app.container.convert_with_ai_use_case._ai_client
                azure_client = ai_client.create_client(
                    azure_endpoint,
                    api_key,
                    api_version
                )
                
                # Get file extension for conversion type detection
                extension = file_info.extension.lower()
                
                yield create_sse_response({
                    "status": "processing",
                    "message": f"Converting {extension} document to images...",
                    "step": "document_conversion"
                }, "progress")
                
                # Convert document to images
                image_processor = current_app.container.convert_with_ai_use_case._image_processor
                try:
                    if extension == '.pdf':
                        image_bytes_list = image_processor.convert_pdf_to_images(temp_file.name, dpi=dpi)
                    elif extension in ['.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls']:
                        image_bytes_list = image_processor.convert_office_document_to_images(temp_file.name, extension, dpi=dpi)
                    else:
                        image_bytes_list = image_processor.convert_document_to_images_basic(temp_file.name)
                except Exception as e:
                    yield create_sse_response({
                        "status": "error",
                        "message": f"Failed to convert document to images: {str(e)}"
                    }, "error")
                    return
                
                total_pages = len(image_bytes_list)
                yield create_sse_response({
                    "status": "processing",
                    "message": f"Document converted to {total_pages} images. Starting AI analysis...",
                    "total_pages": total_pages,
                    "step": "ai_processing_start"
                }, "progress")
                
                # Process each page with streaming
                markdown_pages = []
                analysis_results = []
                successful_pages = 0
                failed_pages = 0
                
                for i, image_bytes in enumerate(image_bytes_list):
                    page_num = i + 1
                    
                    yield create_sse_response({
                        "status": "processing",
                        "message": f"Analyzing page {page_num} of {total_pages}...",
                        "current_page": page_num,
                        "total_pages": total_pages,
                        "step": "ai_page_processing"
                    }, "progress")
                    
                    try:
                        # Stream AI analysis for this page
                        page_markdown = ""
                        for chunk in ai_client.analyze_image_stream(
                            image_bytes, 
                            azure_client, 
                            deployment_name,
                            page_num
                        ):
                            page_markdown += chunk
                            # Send streaming chunk for this page
                            yield create_sse_response({
                                "status": "streaming",
                                "message": f"AI analyzing page {page_num}...",
                                "page": page_num,
                                "chunk": chunk
                            }, "ai_chunk")
                        
                        markdown_pages.append(page_markdown)
                        analysis_results.append({
                            "page": page_num,
                            "status": "success",
                            "content_length": len(page_markdown)
                        })
                        successful_pages += 1
                        
                        yield create_sse_response({
                            "status": "page_completed",
                            "message": f"Page {page_num} analysis completed",
                            "page": page_num,
                            "content_length": len(page_markdown),
                            "progress": f"{page_num}/{total_pages}"
                        }, "page_result")
                        
                    except Exception as e:
                        error_markdown = f"# Page {page_num}\n\n[Error: Failed to analyze this page - {str(e)}]\n\n"
                        markdown_pages.append(error_markdown)
                        analysis_results.append({
                            "page": page_num,
                            "status": "error",
                            "error": str(e)
                        })
                        failed_pages += 1
                        
                        yield create_sse_response({
                            "status": "page_error",
                            "message": f"Failed to analyze page {page_num}",
                            "page": page_num,
                            "error": str(e),
                            "progress": f"{page_num}/{total_pages}"
                        }, "page_error")
                
                # Combine all pages
                combined_markdown = "\n\n---\n\n".join(markdown_pages)
                
                yield create_sse_response({
                    "status": "processing",
                    "message": "All pages processed. Finalizing document...",
                    "step": "post_processing",
                    "pages_processed": total_pages,
                    "successful_pages": successful_pages,
                    "failed_pages": failed_pages
                }, "progress")
                
                # Apply markdown enhancement if requested
                if enhance_markdown:
                    markdown_enhancer = current_app.container.convert_with_ai_use_case._markdown_enhancer
                    combined_markdown = markdown_enhancer.enhance_markdown_structure(
                        combined_markdown, file.filename
                    )

                # Send final completion event
                yield create_sse_response({
                    "status": "completed",
                    "message": "AI conversion completed successfully",
                    "result": {
                        "success": True,
                        "markdown": combined_markdown,
                        "file_info": file_info.__dict__,
                        "analysis_results": analysis_results,
                        "metadata": {
                            "original_filename": file.filename,
                            "converted_size": len(combined_markdown),
                            "pages_processed": total_pages,
                            "successful_pages": successful_pages,
                            "failed_pages": failed_pages,
                            "enhanced": enhance_markdown,
                            "method": "ai_image_analysis_streaming",
                            "llm_model": deployment_name,
                            "azure_endpoint": azure_endpoint,
                            "dpi": dpi if extension == '.pdf' else None
                        }
                    }
                }, "result")
                
            finally:
                current_app.container.file_storage_adapter.cleanup_temp_file(temp_file.name)

        except Exception as e:
            yield create_sse_response({
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }, "error")

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )


def _error_response(error: str, message: str, status_code: int, extra_data: dict = None):
    error_data = {
        'error': error,
        'message': message
    }
    if extra_data:
        error_data.update(extra_data)
    
    return Response(
        json.dumps(error_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=status_code
    )