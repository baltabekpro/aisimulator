#!/bin/bash

# Script to fix MinIO access policies and ensure public access to avatars

# Check if mc (MinIO client) is installed
if ! command -v mc &> /dev/null; then
    echo "Installing MinIO client..."
    wget https://dl.min.io/client/mc/release/linux-amd64/mc
    chmod +x mc
    mv mc /usr/local/bin/
fi

# Configure MinIO client
echo "Configuring MinIO client..."
mc alias set minio http://minio:9000 minioadmin minioadmin

# Create bucket if it doesn't exist
echo "Creating user-files bucket if needed..."
mc mb --ignore-existing minio/user-files

# Set public policy for the bucket
echo "Setting public read policy for the bucket..."

# Create policy file
cat > /tmp/public-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::user-files/*"]
        }
    ]
}
EOF

# Apply policy
mc anonymous set download minio/user-files

echo "MinIO access policy configured successfully"
