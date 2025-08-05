#!/bin/bash

echo "SlideGenie Backend Setup"
echo "========================"
echo ""
echo "Choose your database setup:"
echo "1) Use Supabase (Recommended - No local PostgreSQL needed)"
echo "2) Use Local Docker PostgreSQL (Requires stopping existing PostgreSQL on port 5432)"
echo ""
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "Setting up with Supabase..."
        echo ""
        echo "Please provide your Supabase credentials:"
        echo "(Get these from https://supabase.com dashboard > Settings)"
        echo ""
        read -p "Supabase Project URL (e.g., https://xxxxx.supabase.co): " SUPABASE_URL
        read -p "Supabase Service Key: " SUPABASE_SERVICE_KEY
        read -p "Supabase Database URL: " DATABASE_URL
        
        # Backup current .env
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        
        # Update .env with Supabase settings
        cat > .env.temp << EOF
# Application Settings
APP_NAME=SlideGenie
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# API Settings
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (Supabase)
DATABASE_URL=$DATABASE_URL

# Supabase Configuration
SUPABASE_URL=$SUPABASE_URL
SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY
SUPABASE_STORAGE_BUCKET=documents

# AI API Keys (Keep your existing keys)
EOF
        
        # Append AI keys from existing .env
        grep "OPENAI_API_KEY\|ANTHROPIC_API_KEY" .env >> .env.temp
        
        # Add remaining settings
        cat >> .env.temp << EOF

# OAuth Providers (Optional)
GOOGLE_CLIENT_ID=$(grep GOOGLE_CLIENT_ID .env | cut -d= -f2)
GOOGLE_CLIENT_SECRET=$(grep GOOGLE_CLIENT_SECRET .env | cut -d= -f2)

# File Upload
MAX_UPLOAD_SIZE_MB=50
ALLOWED_UPLOAD_EXTENSIONS=["pdf","docx","doc","pptx","ppt","tex","txt"]

# Export Settings
EXPORT_TIMEOUT_SECONDS=300
MAX_CONCURRENT_EXPORTS=5
EOF
        
        mv .env.temp .env
        echo ""
        echo "✅ Supabase configuration updated!"
        ;;
        
    2)
        echo ""
        echo "Setting up with Local Docker PostgreSQL..."
        echo ""
        echo "⚠️  Port 5432 is currently in use by another PostgreSQL instance."
        echo ""
        echo "You need to stop the existing PostgreSQL service first:"
        echo "  - On macOS: sudo brew services stop postgresql"
        echo "  - Or: sudo killall postgres"
        echo ""
        read -p "Have you stopped the existing PostgreSQL service? (y/n): " stopped
        
        if [ "$stopped" = "y" ]; then
            echo "Starting Docker services..."
            docker-compose up -d postgres redis minio minio-init
        else
            echo "Please stop the existing PostgreSQL service and run this script again."
            exit 1
        fi
        ;;
        
    *)
        echo "Invalid choice. Please run the script again and choose 1 or 2."
        exit 1
        ;;
esac

echo ""
echo "Running database migrations..."
poetry run alembic upgrade head

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "To start the backend server:"
echo "  poetry run uvicorn app.main:app --reload"