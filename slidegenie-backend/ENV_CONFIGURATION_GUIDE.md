# SlideGenie Environment Configuration Guide

## Overview

This document explains the environment configuration for SlideGenie Backend based on a comprehensive analysis of the actual codebase implementation.

## Configuration Categories

### 1. **ESSENTIAL Settings** (Required to run)

These settings are absolutely required for the application to start:

- **Application Settings**: Basic app configuration (name, environment, debug mode)
- **Security**: JWT secret key for authentication (MUST be changed in production)
- **Database**: PostgreSQL connection (the app cannot function without a database)
- **AI API Keys**: At least ONE AI provider (OpenAI or Anthropic) must be configured

### 2. **RECOMMENDED Settings** (For full functionality)

These settings enable important features but the app can start without them:

- **Redis**: Enables caching, rate limiting, real-time updates, and background tasks
  - Without Redis: Performance degradation, no rate limiting, no real-time features
- **Supabase Storage**: Required for file uploads and exports
  - Without storage: No document uploads, no presentation exports

### 3. **OPTIONAL Settings** (Nice to have)

These enhance the application but are not critical:

- **OAuth**: Google/Microsoft login (falls back to email/password auth)
- **Email/SMTP**: Email verification and password reset (can use console output in dev)
- **Sentry**: Error tracking for production
- **Prometheus**: Metrics collection (code is implemented but disabled by default)

## Key Changes from Original Configuration

### Removed/Deprecated

1. **MinIO/S3 Settings**: The codebase has transitioned to Supabase Storage
   - All `MINIO_*` variables are deprecated
   - S3StorageManager exists but is not used

### Added/Updated

1. **Supabase Storage**: Now the primary storage solution
2. **Microsoft OAuth**: Implemented but was missing from original .env
3. **AI Budget Limits**: Cost control features that were implemented
4. **SMTP_TLS**: Email security setting that was implemented

### Clarified

1. **Redis**: Marked as recommended rather than required (app can start without it)
2. **Database**: Emphasized as absolutely required (app cannot function without it)
3. **AI Services**: Clarified that only one provider is required, not both

## Migration Notes

If you're upgrading from an older configuration:

1. **Storage Migration**: Replace MinIO settings with Supabase credentials
2. **Redis**: Can be temporarily disabled if not available
3. **AI Keys**: Ensure at least one provider is configured

## Security Considerations

1. **Never commit** the `.env` file to version control
2. **Always change** the SECRET_KEY in production
3. **Use strong passwords** for database and Redis
4. **Rotate API keys** regularly
5. **Use environment-specific** configurations (dev/staging/prod)

## Quick Start

For minimal local development:

```bash
# Copy the example file
cp .env.example .env

# Edit these required fields:
# - SECRET_KEY (generate a random 32+ character string)
# - POSTGRES_* (your local PostgreSQL settings)
# - Either OPENAI_API_KEY or ANTHROPIC_API_KEY

# Optional but recommended:
# - Set up Redis locally for better performance
# - Configure Supabase for file storage features
```

## Troubleshooting

1. **Database Connection Failed**: Ensure PostgreSQL is running and credentials are correct
2. **AI Features Not Working**: Check that at least one AI API key is valid
3. **File Upload Errors**: Configure Supabase Storage credentials
4. **Rate Limiting Not Working**: Install and configure Redis
5. **Email Not Sending**: Configure SMTP settings or check console in development

## Environment-Specific Settings

- **Development**: Set `DEBUG=true`, use local services
- **Production**: Set `DEBUG=false`, use managed services, configure monitoring
- **Testing**: Use separate database, disable external services