import json
import os
from flask import Blueprint, request, Response, current_app
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