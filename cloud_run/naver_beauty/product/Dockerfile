FROM python:3.11-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc curl unzip \
    && apt-get clean

WORKDIR /app

# requirements 및 코드 복사
COPY . .

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 실행 진입점
ENTRYPOINT ["python", "main.py"]