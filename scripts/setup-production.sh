#!/bin/bash

# Production Setup Script for CKD Early Detection System
# This script helps configure the system for production deployment

set -e

echo "=========================================="
echo "CKD Early Detection System - Production Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Please do not run this script as root"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Install with: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
else
    echo "✅ Docker installed: $(docker --version)"
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    echo "Install with: sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
else
    echo "✅ Docker Compose installed: $(docker-compose --version)"
fi

# Check OpenSSL
if ! command -v openssl &> /dev/null; then
    echo "❌ OpenSSL is not installed"
    echo "Install with: sudo apt-get install openssl"
    exit 1
else
    echo "✅ OpenSSL installed: $(openssl version)"
fi

echo ""
echo "All prerequisites met!"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists"
fi

echo ""
echo "==================================="
echo "Security Configuration"
echo "==================================="
echo ""

# Generate SECRET_KEY
echo "Generating SECRET_KEY..."
SECRET_KEY=$(openssl rand -hex 32)
echo "✅ SECRET_KEY generated"

# Generate ENCRYPTION_KEY
echo "Generating ENCRYPTION_KEY..."
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "⚠️  Could not generate ENCRYPTION_KEY (cryptography package not installed)"
    echo "Install with: pip3 install cryptography"
    ENCRYPTION_KEY="CHANGE-ME-$(openssl rand -hex 32)"
fi
echo "✅ ENCRYPTION_KEY generated"

# Generate database password
echo "Generating database password..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "✅ Database password generated"

# Generate Redis password
echo "Generating Redis password..."
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
echo "✅ Redis password generated"

echo ""
echo "Updating .env file with generated secrets..."

# Update .env file
sed -i.bak "s|SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|g" .env
sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|g" .env
sed -i.bak "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|g" .env
sed -i.bak "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|g" .env
sed -i.bak "s|DEBUG=.*|DEBUG=False|g" .env

# Update DATABASE_URL with new password
sed -i.bak "s|DATABASE_URL=postgresql://ckd_user:.*@|DATABASE_URL=postgresql://ckd_user:${POSTGRES_PASSWORD}@|g" .env

echo "✅ .env file updated with secure values"
echo ""

# Prompt for production domain
read -p "Enter your production domain (or press Enter for localhost): " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="localhost"
fi

# Update CORS_ORIGINS
if [ "$DOMAIN" != "localhost" ]; then
    sed -i.bak "s|CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://${DOMAIN}\"]|g" .env
    echo "✅ CORS_ORIGINS updated to https://${DOMAIN}"
fi

echo ""
echo "==================================="
echo "SSL/TLS Configuration"
echo "==================================="
echo ""

read -p "Do you want to generate SSL certificates now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./scripts/generate-ssl-certs.sh
else
    echo "⚠️  Skipping SSL certificate generation"
    echo "   Run ./scripts/generate-ssl-certs.sh later to generate certificates"
fi

echo ""
echo "==================================="
echo "Directory Setup"
echo "==================================="
echo ""

# Create necessary directories
echo "Creating required directories..."
mkdir -p models
mkdir -p backend/logs
mkdir -p nginx/ssl
mkdir -p postgres
echo "✅ Directories created"

echo ""
echo "==================================="
echo "File Permissions"
echo "==================================="
echo ""

# Set secure permissions
echo "Setting secure file permissions..."
chmod 600 .env
if [ -f "nginx/ssl/key.pem" ]; then
    chmod 600 nginx/ssl/key.pem
fi
if [ -f "nginx/ssl/cert.pem" ]; then
    chmod 644 nginx/ssl/cert.pem
fi
echo "✅ File permissions set"

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "📝 Important Information:"
echo ""
echo "Your generated secrets (save these securely!):"
echo "  SECRET_KEY: ${SECRET_KEY}"
echo "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"
echo "  REDIS_PASSWORD: ${REDIS_PASSWORD}"
echo ""
echo "⚠️  IMPORTANT: These secrets have been saved to .env file"
echo "   Keep this file secure and never commit it to version control!"
echo ""
echo "Next steps:"
echo "1. Review and customize .env file if needed"
echo "2. Place your ML model in: models/sdoh_ckdpred_final.json"
echo "3. Start services:"
echo "   - Development: docker-compose up -d"
echo "   - Production: docker-compose -f docker-compose.prod.yml up -d"
echo "4. Check health: curl -k https://localhost/health"
echo "5. View logs: docker-compose logs -f"
echo ""
echo "📚 For detailed deployment instructions, see DEPLOYMENT.md"
echo ""
