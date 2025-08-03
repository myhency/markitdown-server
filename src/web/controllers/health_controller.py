import json
from flask import Blueprint, Response
from ...infrastructure.utils.file_utils import SUPPORTED_EXTENSIONS


health_bp = Blueprint('health', __name__)

AI_CONVERTIBLE_EXTENSIONS = {
    '.pdf', '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls'
}


@health_bp.route('/', methods=['GET'])
def home():
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


@health_bp.route('/health', methods=['GET'])
def health_check():
    response_data = {'status': 'healthy', 'service': 'markitdown-server'}
    return Response(
        json.dumps(response_data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8'
    )