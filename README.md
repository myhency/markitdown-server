# MarkItDown File Converter Server

Microsoft의 MarkItDown 라이브러리를 사용하여 다양한 파일 형식을 Markdown으로 변환해주는 Python Flask 서버입니다.

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

```python
import requests

# 이미지를 LLM으로 분석하여 마크다운 변환
with open('example.jpg', 'rb') as file:
    files = {'file': ('example.jpg', file)}
    data = {
        'azure_endpoint': 'https://your-resource.openai.azure.com/',
        'api_key': 'your-api-key',
        'deployment_name': 'gpt-4o',
        'format': 'json',
        'enhance_markdown': 'true'
    }

    response = requests.post('http://localhost:5001/convert_image',
                           files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        llm_description = result['markdown']
        print("LLM-generated description:", llm_description)
    else:
        print(f"Error: {response.json()}")
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

제공된 클라이언트 예제를 사용하여 서버를 테스트할 수 있습니다:

```bash
python client_example.py
```

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
