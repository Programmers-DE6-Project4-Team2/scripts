# amd64 아키텍처 명시
FROM --platform=linux/amd64 python:3.11-slim

# 시스템 패키지 설치 (Chrome 포함)
RUN apt-get update && apt-get install -y \
    curl wget gnupg unzip fonts-liberation \
    libnss3 libxss1 libasound2 libatk1.0-0 libgtk-3-0 libgbm-dev libx11-xcb1 \
    x11-utils ca-certificates \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

# 환경 변수 설정
ENV ENV=local

# 환경변수 설정
ENV DISPLAY=:99
ENV PYTHONPATH=/app

# 포트 오픈
EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
