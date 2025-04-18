#!/bin/sh

# Ожидаем, пока MinIO полностью запустится
echo "Waiting for MinIO to start..."
sleep 10

# Создаем алиас для MinIO клиента
/usr/bin/mc config host add minio http://minio:9000 ${S3_ACCESS_KEY:-minioadmin} ${S3_SECRET_KEY:-minioadmin}

# Создаем бакет если он не существует
echo "Creating bucket ${S3_BUCKET_NAME:-user-files}..."
/usr/bin/mc mb --ignore-existing minio/${S3_BUCKET_NAME:-user-files}

# Делаем бакет публичным для чтения
echo "Setting bucket policy to public..."
/usr/bin/mc policy set public minio/${S3_BUCKET_NAME:-user-files}

echo "MinIO initialization completed"
