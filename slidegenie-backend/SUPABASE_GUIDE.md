# Supabase Integration Guide for SlideGenie

## Overview

SlideGenie has been configured to use Supabase as a complete backend solution, replacing multiple services with a single integrated platform. Supabase provides PostgreSQL database, S3-compatible storage, authentication, and real-time capabilities.

## What Supabase Provides

### Free Tier Includes
- **Database**: 500MB PostgreSQL with pgvector extension
- **Storage**: 1GB file storage with S3-compatible API
- **Authentication**: 50,000 monthly active users
- **API Requests**: 50,000/month
- **Real-time**: Websocket connections for live updates
- **Edge Functions**: Serverless functions
- **Full-text Search**: Built-in PostgreSQL capabilities

### Features Replacing Existing Stack
- ✅ PostgreSQL with pgvector (replaces local PostgreSQL)
- ✅ S3-compatible storage (replaces MinIO)
- ✅ Full-text search (replaces Elasticsearch)
- ✅ Real-time subscriptions (replaces Redis pub/sub)
- ✅ Built-in authentication (enhances JWT auth)

## Quick Start Setup

### 1. Create Supabase Project

1. Visit [https://app.supabase.com](https://app.supabase.com)
2. Sign up or log in
3. Click "New project"
4. Configure:
   - **Project name**: slidegenie-backend
   - **Database password**: Choose a strong password
   - **Region**: Select closest to your users
5. Wait for project creation (~2 minutes)

### 2. Get Credentials

In your Supabase dashboard:

1. **API Credentials** (Settings → API):
   - **Project URL**: `https://your-project-id.supabase.co`
   - **anon key**: For frontend (public)
   - **service_role key**: For backend (secret!)

2. **Database Connection** (Settings → Database):
   - **Connection string**: `postgresql://postgres:[YOUR-PASSWORD]@[PROJECT-ID].supabase.co:5432/postgres`

### 3. Configure Environment

Create or update `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SUPABASE_ANON_KEY=your-anon-key-here  # Optional, for frontend

# Database (using Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:your-password@your-project-id.supabase.co:5432/postgres

# Storage Configuration
SUPABASE_STORAGE_BUCKET=documents  # Will be created automatically

# Optional: Disable services not needed for MVP
ENABLE_REDIS=false
ENABLE_ELASTICSEARCH=false
ENABLE_CELERY=false
```

### 4. Set Up Storage Bucket

The storage bucket is created automatically on first use, but you can also create it manually:

1. Go to Storage in Supabase dashboard
2. Click "New bucket"
3. Name: `documents`
4. Set to Private (authenticated access only)
5. Configure policies for user access

## Implementation Details

### Storage Integration

The SlideGenie backend includes a complete Supabase Storage implementation:

**File**: `app/services/document_processing/storage/supabase_storage.py`

Key features:
- Upload/download/delete files
- Metadata management
- Signed URL generation
- File listing and search
- Automatic bucket creation
- Health checks

**Usage Example**:
```python
from app.services.document_processing.storage.storage_manager import StorageManager

# Initialize storage
storage_manager = StorageManager()
await storage_manager.initialize()

# Upload document
file_id, info = await storage_manager.store_document(
    file_content=b"file contents",
    filename="document.pdf",
    content_type="application/pdf",
    user_id=user_uuid,
    metadata={"key": "value"}
)

# Retrieve document
doc = await storage_manager.retrieve_document(
    file_id=file_id,
    user_id=user_uuid,
    include_content=True
)

# Generate signed URL for temporary access
url = await storage_manager.get_signed_url(file_id, expires_in=3600)
```

### File Organization

Files are stored with the following structure:
```
documents/
├── {user_id}/
│   ├── {file_id}/
│   │   └── {original_filename}
```

This ensures:
- User isolation for security
- Unique file identification
- Preservation of original filenames

### Database Migration

1. **Export existing schema** (if you have data):
   ```bash
   pg_dump --schema-only your_local_db > schema.sql
   ```

2. **Import to Supabase**:
   ```bash
   psql -h [YOUR-PROJECT-REF].supabase.co -p 5432 -d postgres -U postgres < schema.sql
   ```

3. **Run Alembic migrations**:
   ```bash
   poetry run alembic upgrade head
   ```

### Mock Components for MVP

For MVP simplicity, mock implementations are provided for:

- **Cache Manager**: In-memory caching (replaces Redis)
- **Search Indexer**: Simple in-memory search (replaces Elasticsearch)
- **Lifecycle Manager**: Basic file lifecycle tracking
- **Backup Manager**: Simple backup scheduling

These can be replaced with real implementations when scaling.

## Testing the Integration

### 1. Test Supabase Connection

```bash
# Test database connection
poetry run python -c "from app.infrastructure.database.base import engine; print('Database connected!')"

# Test storage connection
poetry run python test_supabase_direct.py
```

### 2. Run Full Storage Test

```bash
poetry run python test_supabase_storage.py
```

This will:
- Initialize storage components
- Upload a test document
- Retrieve the document
- Check user quota
- Delete the document
- Display storage metrics
- Perform health check

### 3. Start the Backend

```bash
poetry run uvicorn app.main:app --reload
```

## Security Considerations

### API Keys
- **service_role key**: Full access, keep secret, use only in backend
- **anon key**: Limited access, safe for frontend with RLS
- Never commit keys to version control

### Row Level Security (RLS)
Enable RLS for user data isolation:

```sql
-- Enable RLS on custom tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own documents
CREATE POLICY "Users can access own documents" ON documents
  FOR ALL USING (auth.uid() = user_id);
```

### Storage Security
- All files are private by default
- Access requires authentication
- Use signed URLs for temporary access
- Files organized by user ID for isolation

## Performance Optimization

### Connection Pooling
Configure in `.env`:
```bash
# Database connection pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
```

### Storage Optimization
- Supabase Storage uses CDN for global delivery
- Supports resumable uploads for large files
- Automatic retry on failures
- Connection pooling built-in

### Caching Strategy
- Use Supabase's built-in caching headers
- Implement client-side caching for static content
- Use signed URLs with appropriate expiration

## Scaling Beyond MVP

### When to Upgrade

Consider upgrading when you need:
- More than 500MB database storage
- More than 1GB file storage
- More than 50k API requests/month
- Higher performance requirements

### Production Considerations

1. **Enable Point-in-Time Recovery**
   - Available on Pro plan
   - Automatic backups every 24 hours
   - 7-day retention

2. **Set Up Monitoring**
   - Use Supabase dashboard metrics
   - Configure alerts for usage limits
   - Monitor query performance

3. **Implement Caching**
   - Add Redis for application caching
   - Use CDN for static assets
   - Implement query result caching

4. **Security Hardening**
   - Enable 2FA for Supabase account
   - Rotate API keys regularly
   - Implement IP allowlisting
   - Regular security audits

## Cost Optimization

### Free Tier Best Practices
- Monitor usage in Supabase dashboard
- Implement file size limits (50MB default)
- Clean up old/unused files regularly
- Use efficient queries to minimize API calls

### Production Pricing
- **Pro Plan**: $25/month
  - 8GB database
  - 100GB storage
  - 100GB bandwidth
  - Daily backups
  
- **Pay-as-you-go**:
  - Database: $0.125/GB/month
  - Storage: $0.021/GB/month
  - Bandwidth: $0.09/GB

## Troubleshooting

### Common Issues

1. **"Supabase credentials not configured"**
   - Ensure both `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are in `.env`
   - Check for typos in credentials

2. **"Bucket does not exist"**
   - The bucket is created automatically on first use
   - Check Supabase dashboard under Storage
   - Ensure using service key, not anon key

3. **"File size limit exceeded"**
   - Default limit is 50MB (configurable)
   - Can be increased in Supabase dashboard
   - Check Storage settings

4. **Database connection errors**
   - Verify `DATABASE_URL` is correct
   - Check database password
   - Ensure project is active (not paused)

5. **Permission denied errors**
   - Verify using service key for backend
   - Check RLS policies if enabled
   - Ensure user has necessary permissions

### Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger("app.services.document_processing.storage").setLevel(logging.DEBUG)
```

## Migration from Other Services

### From MinIO/S3
1. Export existing files
2. Use Supabase Storage client to upload
3. Update database references to new paths
4. Update application configuration

### From Local PostgreSQL
1. Export database with `pg_dump`
2. Import to Supabase with `psql`
3. Update connection string
4. Test all queries

### From Redis
1. For caching: Use in-memory cache initially
2. For pub/sub: Use Supabase Realtime
3. For job queues: Consider Supabase Edge Functions

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Storage Guide](https://supabase.com/docs/guides/storage)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [PostgreSQL with Supabase](https://supabase.com/docs/guides/database)
- [Supabase Pricing](https://supabase.com/pricing)
- [Supabase Status](https://status.supabase.com)

## Support

- Supabase Discord: https://discord.supabase.com
- GitHub Issues: https://github.com/supabase/supabase/issues
- Email Support: support@supabase.com (Pro plan and above)