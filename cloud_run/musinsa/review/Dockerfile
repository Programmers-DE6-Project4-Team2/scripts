FROM python:3.9-slim

LABEL maintainer="de6-ez-team"
LABEL description="Musinsa Data Crawler Cloud Run Job with GCS Integration"

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
ENV ENV=cloud_run_job

# Cloud Run Job + Airflow DAG 통합용 환경변수 기본값
ENV JOB_TYPE=product
ENV LOG_LEVEL=INFO
ENV REQUEST_DELAY=1.0
ENV MAX_PAGES=8
ENV REVIEW_PAGES=25

# 데이터 디렉토리 생성
RUN mkdir -p /app/data /app/logs

# Cloud Run Job용 실행 명령어
CMD ["python", "main.py"]
