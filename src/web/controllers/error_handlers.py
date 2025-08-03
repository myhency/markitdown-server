import json
from flask import Flask, Response


def register_error_handlers(app: Flask):
    
    @app.errorhandler(413)
    def too_large(e):
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
        error_data = {
            'error': 'Method not allowed',
            'message': 'The HTTP method is not allowed for this endpoint'
        }
        return Response(
            json.dumps(error_data, ensure_ascii=False, indent=2),
            mimetype='application/json; charset=utf-8',
            status=405
        )