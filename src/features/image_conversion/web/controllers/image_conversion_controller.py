import json
import asyncio
from flask import Blueprint, request, Response, jsonify, stream_with_context
from werkzeug.utils import secure_filename
import tempfile
import os

from ...application.use_cases.convert_image import ConvertImageUseCase
from ...infrastructure.adapters.azure_openai_adapter import AzureOpenAIAdapter
from ...infrastructure.adapters.file_storage_adapter import FileStorageAdapter
from ...domain.models.conversion_request import AIConversionRequest
from ...domain.services.markdown_enhancer import MarkdownEnhancerService
from .....shared.infrastructure.utils.file_utils import allowed_file, get_file_extension, is_image_file


image_conversion_bp = Blueprint('image_conversion', __name__)


def create_sse_response(data, event_type="message"):
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@image_conversion_bp.route('/convert-image/stream', methods=['POST'])
def convert_image_stream():
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
                    "message": "No file provided"
                }, "error")
                return

            file = request.files['file']
            if file.filename == '':
                yield create_sse_response({
                    "status": "error", 
                    "message": "No file selected"
                }, "error")
                return

            # Check if file is an image
            if not is_image_file(file.filename):
                yield create_sse_response({
                    "status": "error",
                    "message": "File must be an image (png, jpg, jpeg, gif, bmp, webp)"
                }, "error")
                return

            # Get request parameters
            azure_endpoint = request.form.get('azure_endpoint')
            api_key = request.form.get('api_key')
            api_version = request.form.get('api_version', '2024-02-01')
            deployment_name = request.form.get('deployment_name')
            enhance_markdown = request.form.get('enhance_markdown', 'false').lower() == 'true'

            # Validate required parameters
            if not all([azure_endpoint, api_key, deployment_name]):
                yield create_sse_response({
                    "status": "error",
                    "message": "Missing required parameters: azure_endpoint, api_key, deployment_name"
                }, "error")
                return

            yield create_sse_response({
                "status": "processing",
                "message": "File uploaded successfully, starting conversion...",
                "filename": file.filename
            }, "progress")

            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                file.save(temp_file.name)
                temp_file_path = temp_file.name

            try:
                yield create_sse_response({
                    "status": "processing",
                    "message": "Initializing AI client...",
                    "step": "ai_init"
                }, "progress")

                # Create use case instance
                ai_client = AzureOpenAIAdapter()
                file_storage = FileStorageAdapter()
                markdown_enhancer = MarkdownEnhancerService()
                
                use_case = ConvertImageUseCase(
                    llm_conversion_engine=ai_client,
                    ai_client=ai_client,
                    file_storage=file_storage,
                    markdown_enhancer=markdown_enhancer
                )

                yield create_sse_response({
                    "status": "processing",
                    "message": "Sending image to AI for analysis...",
                    "step": "ai_processing"
                }, "progress")

                # Create Azure client
                azure_client = ai_client.create_client(
                    azure_endpoint,
                    api_key,
                    api_version
                )

                # Stream AI analysis
                markdown_content = ""
                with open(temp_file_path, 'rb') as f:
                    image_bytes = f.read()
                
                for chunk in ai_client.analyze_image_stream(
                    image_bytes, 
                    azure_client, 
                    deployment_name,
                    file_path=temp_file_path
                ):
                    markdown_content += chunk
                    # Send streaming chunk
                    yield create_sse_response({
                        "status": "streaming",
                        "message": "AI analyzing...",
                        "chunk": chunk
                    }, "ai_chunk")

                yield create_sse_response({
                    "status": "processing",
                    "message": "AI analysis complete, post-processing...",
                    "step": "post_processing"
                }, "progress")

                # Apply markdown enhancement if requested
                if enhance_markdown:
                    markdown_content = markdown_enhancer.enhance_markdown_structure(
                        markdown_content, filename
                    )

                # Create result object
                result = type('Result', (), {
                    'success': True,
                    'markdown': markdown_content,
                    'original_markdown': markdown_content,
                    'title': None,
                    'metadata': {
                        'original_filename': filename,
                        'converted_size': len(markdown_content),
                        'original_size': len(markdown_content),
                        'enhanced': enhance_markdown,
                        'llm_used': True,
                        'llm_model': deployment_name,
                        'azure_endpoint': azure_endpoint
                    }
                })()

                if result.success:

                    # Send completion event
                    yield create_sse_response({
                        "status": "completed",
                        "message": "Conversion completed successfully",
                        "result": {
                            "markdown": result.markdown,
                            "original_markdown": result.original_markdown,
                            "title": result.title,
                            "metadata": result.metadata
                        }
                    }, "result")
                else:
                    yield create_sse_response({
                        "status": "error",
                        "message": f"Conversion failed: {result.error_message}"
                    }, "error")

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

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


@image_conversion_bp.route('/convert-image', methods=['POST'])
def convert_image():
    """Traditional REST endpoint for image conversion"""
    try:
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check if file is an image
        if not is_image_file(file.filename):
            return jsonify({
                'error': 'File must be an image (png, jpg, jpeg, gif, bmp, webp)'
            }), 400

        # Get request parameters
        azure_endpoint = request.form.get('azure_endpoint')
        api_key = request.form.get('api_key')
        api_version = request.form.get('api_version', '2024-02-01')
        deployment_name = request.form.get('deployment_name')
        enhance_markdown = request.form.get('enhance_markdown', 'false').lower() == 'true'

        # Validate required parameters
        if not all([azure_endpoint, api_key, deployment_name]):
            return jsonify({
                'error': 'Missing required parameters: azure_endpoint, api_key, deployment_name'
            }), 400

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        try:
            # Create use case instance
            ai_client = AzureOpenAIAdapter()
            file_storage = FileStorageAdapter()
            markdown_enhancer = MarkdownEnhancerService()
            
            use_case = ConvertImageUseCase(
                llm_conversion_engine=ai_client,
                ai_client=ai_client,
                file_storage=file_storage,
                markdown_enhancer=markdown_enhancer
            )

            # Create request object
            conversion_request = AIConversionRequest(
                file_path=temp_file_path,
                filename=filename,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
                deployment_name=deployment_name,
                enhance_markdown=enhance_markdown
            )

            # Execute conversion
            result = use_case.execute(conversion_request)

            if result.success:
                return jsonify({
                    'success': True,
                    'markdown': result.markdown,
                    'original_markdown': result.original_markdown,
                    'title': result.title,
                    'metadata': result.metadata
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.error_message
                }), 500

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500