# Python 3.9 slim 이미지 사용
FROM python:3.9-slim

# 메타데이터 설정
LABEL maintainer="de6-ez-team"
LABEL description="Musinsa Data Crawler Flask Application with GCS Integration"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 소스 코드 복사
COPY . /app

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 환경변수 설정
ENV PYTHONPATH=/app
ENV ENV=production
ENV PORT=8080
ENV HOST=0.0.0.0

# 데이터 디렉토리 생성
RUN mkdir -p /app/data /app/logs

# 포트 노출
EXPOSE 8080

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Flask 애플리케이션 실행
CMD ["python", "main.py"]
