# Deployment Guide

## Prerequisites
- Ubuntu 20.04 or later
- Docker 20.10 or later
- Docker Compose v2.0 or later
- PostgreSQL 13 or later

## Server Setup

### 1. Install Required Packages
```bash
# Update package list
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 2. Configure Docker TLS
```bash
# Create directory for certificates
mkdir -p ~/.docker/certs

# Generate CA private key and public certificate
openssl genrsa -aes256 -out ~/.docker/certs/ca-key.pem 4096
openssl req -new -x509 -days 365 -key ~/.docker/certs/ca-key.pem -sha256 -out ~/.docker/certs/ca.pem

# Create server key and certificate signing request
openssl genrsa -out ~/.docker/certs/server-key.pem 4096
openssl req -subj "/CN=$HOST" -sha256 -new -key ~/.docker/certs/server-key.pem -out ~/.docker/certs/server.csr

# Sign the server certificate
openssl x509 -req -days 365 -sha256 \
    -in ~/.docker/certs/server.csr \
    -CA ~/.docker/certs/ca.pem \
    -CAkey ~/.docker/certs/ca-key.pem \
    -CAcreateserial \
    -out ~/.docker/certs/server-cert.pem

# Create client key and certificate signing request
openssl genrsa -out ~/.docker/certs/key.pem 4096
openssl req -subj '/CN=client' -new -key ~/.docker/certs/key.pem -out ~/.docker/certs/client.csr

# Sign the client certificate
openssl x509 -req -days 365 -sha256 \
    -in ~/.docker/certs/client.csr \
    -CA ~/.docker/certs/ca.pem \
    -CAkey ~/.docker/certs/ca-key.pem \
    -CAcreateserial \
    -out ~/.docker/certs/cert.pem

# Set correct permissions
chmod -v 0400 ~/.docker/certs/ca-key.pem ~/.docker/certs/key.pem ~/.docker/certs/server-key.pem
chmod -v 0444 ~/.docker/certs/ca.pem ~/.docker/certs/server-cert.pem ~/.docker/certs/cert.pem

# Configure Docker daemon
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "tls": true,
  "tlscacert": "/root/.docker/certs/ca.pem",
  "tlscert": "/root/.docker/certs/server-cert.pem",
  "tlskey": "/root/.docker/certs/server-key.pem",
  "tlsverify": true,
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"]
}
EOF

# Copy certificates to root directory
sudo mkdir -p /root/.docker/certs
sudo cp ~/.docker/certs/* /root/.docker/certs/

# Restart Docker daemon
sudo systemctl restart docker
```

### 3. Configure PostgreSQL
```bash
# Create data directory
sudo mkdir -p /data/postgres
sudo chown -R 999:999 /data/postgres

# Create environment file
cat > .env <<EOF
POSTGRES_USER=shark_explorer
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=shark_explorer
EOF
```

### 4. Deploy Application

```bash
# Clone repository
git clone https://github.com/your-repo/shark-explorer.git
cd shark-explorer

# Start services
docker compose up -d

# Check logs
docker compose logs -f
```

### 5. Configure Nginx (Optional)
```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/shark-explorer.conf <<EOF
server {
    listen 80;
    server_name explorer.your-domain.com;

    location / {
        proxy_pass http://localhost:8082;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/shark-explorer.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Monitoring Setup

### 1. Deploy Monitoring Stack
```bash
# Start monitoring services
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana
# Open http://your-server:3000
# Default credentials: admin/admin
```

## Backup Procedures

### 1. Database Backup
```bash
# Create backup directory
mkdir -p /backup/postgres

# Create backup script
cat > backup.sh <<EOF
#!/bin/bash
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
docker exec postgres pg_dump -U shark_explorer shark_explorer > /backup/postgres/backup_\${TIMESTAMP}.sql
EOF

chmod +x backup.sh

# Add to crontab
echo "0 0 * * * /path/to/backup.sh" | crontab -
```

## Recovery Procedures

### 1. Database Recovery
```bash
# Restore from backup
cat /backup/postgres/backup_file.sql | docker exec -i postgres psql -U shark_explorer shark_explorer
```

## Security Considerations

1. Always use strong passwords
2. Keep system and Docker up to date
3. Use UFW (Uncomplicated Firewall) to restrict access
4. Regularly rotate TLS certificates
5. Monitor system logs for suspicious activity
6. Back up certificates and configurations 