#!/bin/bash

# Script to fix MinIO avatar previews

# Function to check if service is running
check_service() {
  container_name=$1
  if docker ps | grep -q $container_name; then
    echo "$container_name is running."
    return 0
  else
    echo "$container_name is not running."
    return 1
  fi
}

# Configure MinIO for public access
echo "Setting up MinIO public access..."

# Check if MinIO is running
if check_service "minio"; then
  # Using docker exec to run mc commands inside the container
  docker exec -it minio mc alias set local http://localhost:9000 minioadmin minioadmin
  docker exec -it minio mc anonymous set download local/user-files
  echo "Set public read access for user-files bucket"
  
  # Create policy to ensure public access
  echo '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": ["arn:aws:s3:::user-files/*"]
      }
    ]
  }' > /tmp/public-policy.json
  
  # Apply policy
  docker cp /tmp/public-policy.json minio:/tmp/
  docker exec -it minio mc admin policy create local-public /tmp/public-policy.json
  docker exec -it minio mc admin policy set local-public user=minioadmin
  
  echo "MinIO public access configured successfully"
else
  echo "Unable to configure MinIO - container not found"
fi

echo "Setting up URL proxy for MinIO..."
# Check if nginx is available or we need to set one up
if command -v nginx > /dev/null; then
  echo "Creating nginx config for MinIO proxy..."
  sudo tee /etc/nginx/conf.d/minio-proxy.conf > /dev/null << EOF
server {
    listen 80;
    server_name minio.local;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
  sudo nginx -t && sudo systemctl reload nginx
  echo "Added minio.local proxy - add this to your hosts file"
fi

echo "Done!"
