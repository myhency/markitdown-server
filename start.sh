#!/bin/bash
# MarkItDown Server 시작 스크립트

# 환경 변수 설정
export FLASK_ENV=production
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🚀 Starting MarkItDown Server with Gunicorn..."
echo "📁 Working directory: $(pwd)"
echo "🌐 Server will be available at: http://localhost:5001"

# Gunicorn으로 서버 시작
exec gunicorn \
    --config gunicorn.conf.py \
    --bind 0.0.0.0:5001 \
    --workers 4 \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000 \
    --preload \
    main:app