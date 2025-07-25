#!/bin/bash

# Load secrets from .env
export $(grep -v '^#' .env | xargs)

# 사용자 설정
MODEL_REPO="WhitePeak/bert-base-cased-Korean-sentiment"
HF_TOKEN="$HF_TOKEN"

SPARK_VERSION=3.3.4
HADOOP_VERSION=3
SCALA_VERSION=2.12

MODEL_PATH=/opt/models/korean-sentiment
KEY_PATH=/opt/keys/sa-spark.json
SPARK_HOME=/opt/spark
VENV_DIR=/opt/pyenvs/spark-env

# ① 시스템 패키지 설치
sudo apt-get update -y
sudo apt-get install -y openjdk-17-jdk python3.10 python3.10-venv \
                        python3-pip build-essential wget curl git unzip

# ② Python 가상환경
python3.10 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# ③ Spark 설치
wget -q "https://downloads.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz"
sudo tar -xzf "spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" -C /opt
sudo mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" "$SPARK_HOME"
sudo chown -R "$USER":"$USER" "$SPARK_HOME"

# ④ BigQuery·GCS 커넥터
mkdir -p "$SPARK_HOME/jars"
wget -P "$SPARK_HOME/jars" \
  "https://storage.googleapis.com/spark-lib/bigquery/spark-bigquery-with-dependencies_${SCALA_VERSION}.jar"
wget -P "$SPARK_HOME/jars" \
  "https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop3-latest.jar"

# ⑤ 모델 다운로드
mkdir -p "$MODEL_PATH"
python - <<PY
from huggingface_hub import snapshot_download
print("[INFO] Downloading model…")
snapshot_download("$MODEL_REPO",
                  local_dir="$MODEL_PATH",
                  local_dir_use_symlinks=False,
                  token="$HF_TOKEN")
PY

# ⑥ 환경변수 등록
sudo tee /etc/profile.d/spark_env.sh >/dev/null <<EOF
export JAVA_HOME=\$(dirname \$(dirname \$(readlink -f \$(which javac))))
export SPARK_HOME=$SPARK_HOME
export PATH=\$PATH:\$SPARK_HOME/bin
export PYSPARK_PYTHON=$VENV_DIR/bin/python
export PYSPARK_DRIVER_PYTHON=$VENV_DIR/bin/python
export MODEL_PATH=$MODEL_PATH
export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH
EOF

echo "✅  설치 완료! 새 터미널에서 'source /etc/profile' 후 spark-submit --version 확인."
