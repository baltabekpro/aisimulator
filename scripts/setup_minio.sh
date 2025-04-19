#!/bin/bash

# Install MinIO client if not present
if ! command -v mc &> /dev/null; then
  echo "Installing MinIO client..."
  wget https://dl.min.io/client/mc/release/linux-amd64/mc
  chmod +x mc
  sudo mv mc /usr/local/bin/
fi

# Configure MinIO client
mc alias set minio http://minio:9000 minioadmin minioadmin

# Create bucket if it doesn't exist
mc mb --ignore-existing minio/user-files

# Set bucket policy to public (read-only)
cat > /tmp/policy.json << EOF
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

# Apply the policy
mc admin policy add minio publicread /tmp/policy.json
mc admin policy set minio publicread user=minioadmin

# Set bucket policy
mc anonymous set download minio/user-files

echo "MinIO configuration completed successfully"
