#!/bin/bash

# Script to generate SSL certificates for CKD Early Detection System
# Supports self-signed certificates for development/testing

set -e

echo "==================================="
echo "SSL Certificate Generation Script"
echo "==================================="
echo ""

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Check if certificates already exist
if [ -f "nginx/ssl/cert.pem" ] && [ -f "nginx/ssl/key.pem" ]; then
    echo "⚠️  SSL certificates already exist in nginx/ssl/"
    read -p "Do you want to overwrite them? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Existing certificates preserved."
        exit 0
    fi
fi

echo "Select certificate type:"
echo "1) Self-signed certificate (for development/testing)"
echo "2) Let's Encrypt certificate (for production)"
echo "3) Use existing certificate files"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Generating self-signed certificate..."
        echo ""
        
        # Prompt for certificate details
        read -p "Country Code (e.g., US): " country
        read -p "State/Province: " state
        read -p "City: " city
        read -p "Organization: " org
        read -p "Common Name (domain or IP): " cn
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=${country}/ST=${state}/L=${city}/O=${org}/CN=${cn}"
        
        echo ""
        echo "✅ Self-signed certificate generated successfully!"
        echo "   Certificate: nginx/ssl/cert.pem"
        echo "   Private Key: nginx/ssl/key.pem"
        echo "   Valid for: 365 days"
        echo ""
        echo "⚠️  Note: Self-signed certificates will show security warnings in browsers."
        echo "   Use Let's Encrypt for production deployments."
        ;;
        
    2)
        echo ""
        echo "Setting up Let's Encrypt certificate..."
        echo ""
        
        # Check if certbot is installed
        if ! command -v certbot &> /dev/null; then
            echo "❌ certbot is not installed."
            echo "Install it with: sudo apt-get install certbot"
            exit 1
        fi
        
        read -p "Enter your domain name: " domain
        read -p "Enter your email address: " email
        
        echo ""
        echo "Obtaining certificate from Let's Encrypt..."
        echo "Note: Your domain must be publicly accessible and pointing to this server."
        echo ""
        
        sudo certbot certonly --standalone \
            -d "$domain" \
            --email "$email" \
            --agree-tos \
            --non-interactive
        
        # Copy certificates
        sudo cp "/etc/letsencrypt/live/${domain}/fullchain.pem" nginx/ssl/cert.pem
        sudo cp "/etc/letsencrypt/live/${domain}/privkey.pem" nginx/ssl/key.pem
        sudo chown $(whoami):$(whoami) nginx/ssl/cert.pem nginx/ssl/key.pem
        
        echo ""
        echo "✅ Let's Encrypt certificate obtained successfully!"
        echo "   Certificate: nginx/ssl/cert.pem"
        echo "   Private Key: nginx/ssl/key.pem"
        echo ""
        echo "📝 Set up auto-renewal with: sudo certbot renew --dry-run"
        ;;
        
    3)
        echo ""
        echo "Using existing certificate files..."
        echo ""
        read -p "Enter path to certificate file: " cert_path
        read -p "Enter path to private key file: " key_path
        
        if [ ! -f "$cert_path" ]; then
            echo "❌ Certificate file not found: $cert_path"
            exit 1
        fi
        
        if [ ! -f "$key_path" ]; then
            echo "❌ Private key file not found: $key_path"
            exit 1
        fi
        
        cp "$cert_path" nginx/ssl/cert.pem
        cp "$key_path" nginx/ssl/key.pem
        
        echo ""
        echo "✅ Certificate files copied successfully!"
        ;;
        
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

# Set proper permissions
chmod 644 nginx/ssl/cert.pem
chmod 600 nginx/ssl/key.pem

echo ""
echo "Setting proper file permissions..."
echo "  cert.pem: 644 (readable)"
echo "  key.pem: 600 (secure)"

# Generate DH parameters if they don't exist
if [ ! -f "nginx/dhparam.pem" ]; then
    echo ""
    echo "Generating DH parameters (this may take several minutes)..."
    openssl dhparam -out nginx/dhparam.pem 4096
    chmod 644 nginx/dhparam.pem
    echo "✅ DH parameters generated: nginx/dhparam.pem"
else
    echo ""
    echo "ℹ️  DH parameters already exist: nginx/dhparam.pem"
fi

# Verify certificate
echo ""
echo "Verifying certificate..."
openssl x509 -in nginx/ssl/cert.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After)"

echo ""
echo "==================================="
echo "✅ SSL setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Review your .env file and set production values"
echo "2. Start the services: docker-compose up -d"
echo "3. Test TLS 1.3: openssl s_client -connect localhost:443 -tls1_3"
echo ""
