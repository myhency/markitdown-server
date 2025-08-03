# MarkItDown File Converter Server

Microsoft의 MarkItDown 라이브러리를 사용하여 다양한 파일 형식을 Markdown으로 변환해주는 Python Flask 서버입니다.

## 📋 목차

- [🏗️ 아키텍처](#️-아키텍처)
- [🚀 주요 기능](#-주요-기능)
- [📁 지원하는 파일 형식](#-지원하는-파일-형식)
- [🛠️ 설치 및 실행](#️-설치-및-실행)
- [📖 API 사용법](#-api-사용법)
- [🐍 Python 클라이언트 예제](#-python-클라이언트-예제)
- [📚 API Reference](#-api-reference)
- [🔧 고급 설정](#-고급-설정)
- [🧪 테스트](#-테스트)
- [📝 에러 처리](#-에러-처리)

## 🏗️ 아키텍처

이 프로젝트는 **Feature-based Hexagonal Architecture**를 사용합니다:

- **`src/features/`**: 기능별로 구성된 모듈들
  - `file_conversion/`: 일반 파일 변환 기능
  - `image_conversion/`: 이미지 AI 변환 기능  
  - `ai_conversion/`: 문서의 AI 변환 기능
  - `health/`: 헬스체크 기능
- **`src/shared/`**: 공통 기능 (설정, 유틸리티, 공통 모델)
- **`src/web/`**: 웹 애플리케이션 팩토리 및 의존성 주입

각 기능은 독립적인 `application`, `domain`, `infrastructure` 레이어를 가집니다.

## 🚀 주요 기능

-   **다양한 파일 형식 지원**: Office 문서, PDF, 이미지, 오디오, 텍스트 파일 등
-   **REST API**: 간단한 HTTP POST 요청으로 파일 변환
-   **두 가지 응답 형식**: JSON 또는 순수 텍스트
-   **실시간 스트리밍**: SSE(Server-Sent Events)를 통한 실시간 진행상황 및 AI 응답 스트리밍
-   **마크다운 구조 개선**: 텍스트를 더 읽기 좋은 마크다운으로 후처리
-   **AI 이미지 설명**: Azure OpenAI를 사용한 이미지 내용 분석 및 마크다운 변환
-   **에러 처리**: 자세한 에러 메시지와 상태 코드
-   **Docker 지원**: 컨테이너화된 배포

## 📁 지원하는 파일 형식

-   **Office 문서**: `.docx`, `.doc`, `.pptx`, `.ppt`, `.xlsx`, `.xls`
-   **PDF**: `.pdf`
-   **이미지**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`
-   **오디오**: `.wav`, `.mp3`
-   **텍스트**: `.txt`, `.csv`, `.json`, `.xml`, `.html`, `.htm`
-   **아카이브**: `.zip`
-   **전자책**: `.epub`
-   **Outlook**: `.msg`

## 🛠️ 설치 및 실행

### 로컬 환경에서 실행

1. **저장소 클론 및 의존성 설치**

```bash
git clone <repository-url>
cd markitdown-server
pip install -r requirements.txt
```

2. **서버 실행**

```bash
python main.py
```

서버가 `http://localhost:5001`에서 실행됩니다.

### Docker를 사용한 실행

1. **Docker 이미지 빌드**

```bash
docker build -t markitdown-server .
```

2. **컨테이너 실행**

```bash
docker run -p 5001:5001 markitdown-server
```

## 📖 API 사용법

### 1. 서버 상태 확인

```bash
curl http://localhost:5001/health
```

### 2. 서버 정보 및 지원 형식 확인

```bash
curl http://localhost:5001/
```

### 3. 파일 변환

#### JSON 형식으로 응답받기 (기본값, 마크다운 구조 개선 적용)

```bash
curl -X POST \
  -F "file=@example.pdf" \
  -F "format=json" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert
```

### 4. 이미지 변환 (Azure OpenAI)

#### 전통적인 REST API

```bash
curl -X POST \
  -F "file=@example.jpg" \
  -F "azure_endpoint=https://your-resource.openai.azure.com" \
  -F "api_key=your-api-key" \
  -F "deployment_name=gpt-4o" \
  -F "api_version=2024-10-21" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert-image
```

#### SSE 스트리밍 API (실시간 AI 응답)

```bash
curl -N -X POST \
  -F "file=@example.jpg" \
  -F "azure_endpoint=https://your-resource.openai.azure.com" \
  -F "api_key=your-api-key" \
  -F "deployment_name=gpt-4o" \
  -F "api_version=2024-10-21" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert-image/stream
```

**SSE 이벤트 타입:**
- `connection`: 연결 확립
- `progress`: 진행상황 업데이트  
- `ai_chunk`: 실시간 AI 응답 청크
- `result`: 최종 결과
- `error`: 오류 발생

#### 원본 텍스트만 (마크다운 구조화 없이)

```bash
curl -X POST \
  -F "file=@example.pdf" \
  -F "format=json" \
  -F "enhance_markdown=false" \
  http://localhost:5001/convert
```

응답 예시:

```json
{
    "success": true,
    "markdown": "# 문서 제목\n\n**중요 정보**: 내용...",
    "original_markdown": "문서 제목\n\n중요 정보: 내용...",
    "file_info": {
        "filename": "example.pdf",
        "extension": ".pdf",
        "mimetype": "application/pdf",
        "supported": true
    },
    "processing_info": {
        "enhanced": true
    },
    "metadata": {
        "original_filename": "example.pdf",
        "converted_size": 1456,
        "original_size": 1234,
        "title": "문서 제목"
    }
}
```

#### 순수 텍스트로 응답받기

```bash
curl -X POST \
  -F "file=@example.pdf" \
  -F "format=text" \
  http://localhost:5001/convert
```

## 🐍 Python 클라이언트 예제

### 일반 파일 변환

```python
import requests

# 파일 변환 (마크다운 구조 개선 적용)
with open('example.pdf', 'rb') as file:
    files = {'file': ('example.pdf', file)}
    data = {'format': 'json', 'enhance_markdown': 'true'}

    response = requests.post('http://localhost:5001/convert',
                           files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        enhanced_markdown = result['markdown']
        original_markdown = result['original_markdown']
        print("Enhanced:", enhanced_markdown)
        print("Original:", original_markdown)
    else:
        print(f"Error: {response.json()}")
```

### 이미지 변환 (Azure OpenAI 사용)

#### 전통적인 REST API 방식

```python
import requests

# 이미지를 LLM으로 분석하여 마크다운 변환
with open('example.jpg', 'rb') as file:
    files = {'file': ('example.jpg', file)}
    data = {
        'azure_endpoint': 'https://your-resource.openai.azure.com/',
        'api_key': 'your-api-key',
        'deployment_name': 'gpt-4o',
        'api_version': '2024-10-21',
        'enhance_markdown': 'true'
    }

    response = requests.post('http://localhost:5001/convert-image',
                           files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        llm_description = result['markdown']
        print("LLM-generated description:", llm_description)
    else:
        print(f"Error: {response.json()}")
```

#### SSE 스트리밍 방식 (실시간 진행상황 및 AI 응답)

```python
import requests
import json

# SSE 스트리밍으로 실시간 AI 응답 받기
with open('example.jpg', 'rb') as file:
    files = {'file': ('example.jpg', file)}
    data = {
        'azure_endpoint': 'https://your-resource.openai.azure.com/',
        'api_key': 'your-api-key',
        'deployment_name': 'gpt-4o',
        'api_version': '2024-10-21',
        'enhance_markdown': 'true'
    }

    response = requests.post('http://localhost:5001/convert-image/stream',
                           files=files, data=data, stream=True)

    if response.status_code == 200:
        ai_content = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        event_data = json.loads(line[6:])
                        status = event_data.get('status')
                        
                        if status == 'streaming':
                            # 실시간 AI 응답 청크
                            chunk = event_data.get('chunk', '')
                            ai_content += chunk
                            print(chunk, end='', flush=True)
                        elif status == 'completed':
                            # 최종 결과
                            result = event_data.get('result', {})
                            print(f"\n\n완료! 최종 마크다운:\n{result.get('markdown')}")
                        elif status == 'error':
                            print(f"Error: {event_data.get('message')}")
                            break
                        else:
                            # 진행상황 업데이트
                            print(f"Status: {event_data.get('message')}")
                    except json.JSONDecodeError:
                        continue
    else:
        print(f"Error: {response.status_code}")
```

### 문서의 AI 변환 (Azure OpenAI 사용)

```python
import requests

# 문서를 이미지로 변환한 후 AI로 분석
with open('example.pdf', 'rb') as file:
    files = {'file': ('example.pdf', file)}
    data = {
        'azure_endpoint': 'https://your-resource.openai.azure.com/',
        'api_key': 'your-api-key',
        'deployment_name': 'gpt-4o',
        'dpi': '200',
        'format': 'json',
        'enhance_markdown': 'true'
    }

    response = requests.post('http://localhost:5001/convert_with_ai',
                           files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        ai_analysis = result['markdown']
        print("AI-analyzed content:", ai_analysis)
        print(f"Pages processed: {result['metadata']['pages_processed']}")
    else:
        print(f"Error: {response.json()}")
```

## 🔧 고급 설정

### 환경 변수

-   `FLASK_ENV`: 개발/프로덕션 환경 설정
-   `MAX_CONTENT_LENGTH`: 최대 파일 크기 (기본값: 100MB)

### Azure OpenAI 설정

이미지 분석 기능을 사용하려면 Azure OpenAI 서비스가 필요합니다:

**지원하는 모델:**
- `gpt-4o` (권장)
- `gpt-4-vision-preview` 
- `gpt-4o-mini` (제한적 지원)

**필수 매개변수:**
- `azure_endpoint`: Azure OpenAI 엔드포인트 URL
- `api_key`: Azure OpenAI API 키
- `deployment_name`: 배포된 모델 이름
- `api_version`: API 버전 (예: 2024-10-21)

**참고:** `gpt-4o-mini`는 이미지 분석을 지원하지 않을 수 있습니다. 최적의 성능을 위해 `gpt-4o` 사용을 권장합니다.

### 프로덕션 배포

프로덕션 환경에서는 Gunicorn WSGI 서버를 사용합니다:

#### 개발 환경
```bash
python main.py
```

#### 프로덕션 환경
```bash
# Gunicorn 설치 (이미 requirements.txt에 포함됨)
pip install gunicorn

# 간단한 실행
gunicorn main:app

# 또는 제공된 스크립트 사용
./start.sh

# 또는 설정 파일과 함께 실행
gunicorn --config gunicorn.conf.py main:app
```

설정 파일 `gunicorn.conf.py`에서 워커 수, 타임아웃, 로깅 등을 조정할 수 있습니다.

## 🧪 테스트

### CLI 테스트

제공된 클라이언트 예제를 사용하여 서버를 테스트할 수 있습니다:

```bash
python client_example.py
```

### SSE 스트리밍 테스트

브라우저에서 SSE 스트리밍을 테스트할 수 있는 HTML 파일이 제공됩니다:

```bash
# 서버 실행 후
open sse_test.html
```

이 페이지에서는 다음을 테스트할 수 있습니다:
- 실시간 이미지 분석 진행상황
- AI 응답 스트리밍
- 전통적인 REST API와의 비교
- 다양한 이벤트 타입 확인

### API 테스트 예제

```bash
# 일반 파일 변환
curl -X POST -F "file=@example.pdf" http://localhost:5001/convert

# 이미지 분석 (REST)
curl -X POST \
  -F "file=@example.jpg" \
  -F "azure_endpoint=https://your-endpoint.openai.azure.com" \
  -F "api_key=your-key" \
  -F "deployment_name=gpt-4o" \
  http://localhost:5001/convert-image

# 이미지 분석 (SSE 스트리밍)
curl -N -X POST \
  -F "file=@example.jpg" \
  -F "azure_endpoint=https://your-endpoint.openai.azure.com" \
  -F "api_key=your-key" \
  -F "deployment_name=gpt-4o" \
  http://localhost:5001/convert-image/stream
```

## 📚 API Reference

### Base URL
```
http://localhost:5001
```

### Authentication
- No authentication required for basic file conversion
- Azure OpenAI API key required for AI-powered features

---

### 1. GET `/`
**서버 정보 및 지원 형식 조회**

#### Response
```json
{
  "status": "MarkItDown File Converter Server",
  "version": "1.0.0",
  "supported_formats": [".docx", ".pdf", ".jpg", ...],
  "endpoints": { ... }
}
```

---

### 2. GET `/health`
**서버 상태 확인**

#### Response
```json
{
  "status": "healthy",
  "service": "markitdown-server"
}
```

---

### 3. POST `/convert`
**일반 파일을 마크다운으로 변환**

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | 변환할 파일 |
| `format` | String | No | `"json"` | 응답 형식: `"json"` 또는 `"text"` |
| `enhance_markdown` | String | No | `"true"` | 마크다운 구조 개선: `"true"` 또는 `"false"` |

#### Request Example
```bash
curl -X POST \
  -F "file=@example.pdf" \
  -F "format=json" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert
```

#### Response (JSON)
```json
{
  "success": true,
  "markdown": "# 문서 제목\n\n**내용**...",
  "original_markdown": "문서 제목\n\n내용...",
  "file_info": {
    "filename": "example.pdf",
    "extension": ".pdf",
    "mimetype": "application/pdf",
    "supported": true
  },
  "processing_info": {
    "enhanced": true
  },
  "metadata": {
    "original_filename": "example.pdf",
    "converted_size": 1456,
    "original_size": 1234,
    "title": "문서 제목"
  }
}
```

#### Response (Text)
```
# 문서 제목

**내용**...
```

---

### 4. POST `/convert-image`
**이미지를 AI로 분석하여 마크다운으로 변환 (REST API)**

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | 분석할 이미지 파일 |
| `azure_endpoint` | String | Yes | - | Azure OpenAI 엔드포인트 URL |
| `api_key` | String | Yes | - | Azure OpenAI API 키 |
| `deployment_name` | String | Yes | - | Azure OpenAI 배포 이름 |
| `api_version` | String | No | `"2024-02-01"` | Azure OpenAI API 버전 |
| `enhance_markdown` | String | No | `"true"` | 마크다운 구조 개선 여부 |

#### Request Example
```bash
curl -X POST \
  -F "file=@image.jpg" \
  -F "azure_endpoint=https://your-resource.openai.azure.com" \
  -F "api_key=your-api-key" \
  -F "deployment_name=gpt-4o" \
  -F "api_version=2024-10-21" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert-image
```

#### Response
```json
{
  "success": true,
  "markdown": "# 이미지 분석\n\n[Image: 돼지 얼굴 그림...]",
  "original_markdown": "이미지 분석\n\n[Image: 돼지 얼굴 그림...]",
  "title": null,
  "metadata": {
    "original_filename": "image.jpg",
    "converted_size": 123,
    "original_size": 123,
    "enhanced": true,
    "llm_used": true,
    "llm_model": "gpt-4o",
    "azure_endpoint": "https://your-resource.openai.azure.com"
  }
}
```

---

### 5. POST `/convert-image/stream`
**이미지를 AI로 분석하여 마크다운으로 변환 (SSE 스트리밍)**

#### Parameters
동일한 parameters를 `/convert-image`와 동일하게 사용

#### Request Example
```bash
curl -N -X POST \
  -F "file=@image.jpg" \
  -F "azure_endpoint=https://your-resource.openai.azure.com" \
  -F "api_key=your-api-key" \
  -F "deployment_name=gpt-4o" \
  -F "api_version=2024-10-21" \
  -F "enhance_markdown=true" \
  http://localhost:5001/convert-image/stream
```

#### Response (Server-Sent Events)

##### Connection Event
```
event: connection
data: {"status": "connected", "message": "Connection established"}
```

##### Progress Events
```
event: progress
data: {"status": "processing", "message": "File uploaded successfully, starting conversion...", "filename": "image.jpg"}

event: progress
data: {"status": "processing", "message": "Initializing AI client...", "step": "ai_init"}

event: progress
data: {"status": "processing", "message": "Sending image to AI for analysis...", "step": "ai_processing"}
```

##### AI Streaming Events
```
event: ai_chunk
data: {"status": "streaming", "message": "AI analyzing...", "chunk": "# 이미지"}

event: ai_chunk
data: {"status": "streaming", "message": "AI analyzing...", "chunk": " 분석"}
```

##### Post-processing Event
```
event: progress
data: {"status": "processing", "message": "AI analysis complete, post-processing...", "step": "post_processing"}
```

##### Final Result Event
```
event: result
data: {
  "status": "completed",
  "message": "Conversion completed successfully",
  "result": {
    "markdown": "# 이미지 분석\n\n[Image: 상세한 설명...]",
    "original_markdown": "이미지 분석\n\n[Image: 상세한 설명...]",
    "title": null,
    "metadata": { ... }
  }
}
```

##### Error Event
```
event: error
data: {"status": "error", "message": "Error description"}
```

---

### 6. POST `/convert_image` (Legacy)
**레거시 이미지 변환 엔드포인트**

동일한 parameters를 `/convert-image`와 동일하게 사용하지만, 내부적으로 다른 구현을 사용합니다.

---

### 7. POST `/convert_with_ai`
**문서를 이미지로 변환한 후 AI로 분석**

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | Yes | - | 변환할 문서 파일 |
| `azure_endpoint` | String | Yes | - | Azure OpenAI 엔드포인트 URL |
| `api_key` | String | Yes | - | Azure OpenAI API 키 |
| `deployment_name` | String | Yes | - | Azure OpenAI 배포 이름 |
| `api_version` | String | No | `"2024-02-01"` | Azure OpenAI API 버전 |
| `dpi` | String | No | `"200"` | PDF 변환 시 DPI 설정 |
| `format` | String | No | `"json"` | 응답 형식 |
| `enhance_markdown` | String | No | `"true"` | 마크다운 구조 개선 여부 |

#### Request Example
```bash
curl -X POST \
  -F "file=@document.pdf" \
  -F "azure_endpoint=https://your-resource.openai.azure.com" \
  -F "api_key=your-api-key" \
  -F "deployment_name=gpt-4o" \
  -F "dpi=200" \
  http://localhost:5001/convert_with_ai
```

#### Response
```json
{
  "success": true,
  "markdown": "# 문서 분석 결과\n\n## 페이지 1\n...",
  "original_markdown": "문서 분석 결과\n\n페이지 1\n...",
  "title": "문서 분석 결과",
  "metadata": {
    "original_filename": "document.pdf",
    "pages_processed": 3,
    "successful_pages": 3,
    "failed_pages": 0,
    "llm_used": true,
    "llm_model": "gpt-4o"
  }
}
```

---

### Error Responses

모든 엔드포인트는 오류 시 다음 형식으로 응답합니다:

#### 400 Bad Request
```json
{
  "error": "No file provided"
}
```

#### 413 Payload Too Large
```json
{
  "error": "File size exceeds maximum limit"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Internal server error description",
  "success": false
}
```

---

### Supported File Formats

| Category | Extensions |
|----------|------------|
| Office Documents | `.docx`, `.doc`, `.pptx`, `.ppt`, `.xlsx`, `.xls` |
| PDF | `.pdf` |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp` |
| Audio | `.wav`, `.mp3` |
| Text | `.txt`, `.csv`, `.json`, `.xml`, `.html`, `.htm` |
| Archive | `.zip` |
| E-book | `.epub` |
| Email | `.msg` |

---

### Azure OpenAI Model Requirements

| Feature | Supported Models | Recommended |
|---------|------------------|-------------|
| Image Analysis | `gpt-4o`, `gpt-4-vision-preview`, `gpt-4o-mini`* | `gpt-4o` |
| Document AI | `gpt-4o`, `gpt-4-vision-preview` | `gpt-4o` |

*`gpt-4o-mini` has limited vision capabilities

---

### Rate Limits

- No built-in rate limiting on the server
- Rate limits may apply based on Azure OpenAI service limits
- Maximum file size: 100MB (configurable)

## 📝 에러 처리

서버는 다음과 같은 HTTP 상태 코드를 반환합니다:

-   `200`: 성공
-   `400`: 잘못된 요청 (파일 없음, 지원하지 않는 형식 등)
-   `413`: 파일 크기 초과
-   `500`: 내부 서버 오류

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙏 감사의 말

이 프로젝트는 Microsoft의 [MarkItDown](https://github.com/microsoft/markitdown) 라이브러리를 기반으로 합니다.
