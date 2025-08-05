# Supabase Setup Instructions for SlideGenie

## Step 1: Get Your Supabase Credentials

1. Go to [https://supabase.com](https://supabase.com) and sign in/create account
2. Create a new project (or use existing one)
3. Once project is created, go to **Settings** (gear icon in sidebar)
4. Navigate to **API** section
5. Copy these values:
   - **Project URL**: `https://[YOUR-PROJECT-REF].supabase.co`
   - **anon (public) key**: `eyJ...` (long string)
   - **service_role (secret) key**: `eyJ...` (different long string) 

6. Navigate to **Database** section
7. Copy the **Connection string** - choose "URI" tab
   - It looks like: `postgresql://postgres:[YOUR-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres`

## Step 2: Create Storage Bucket

1. In Supabase dashboard, go to **Storage** (bucket icon in sidebar)
2. Click "New bucket"
3. Name it: `documents`
4. Set it to **Private** (authenticated access only)
5. Click "Create bucket"

## Step 3: Update Your .env File

Replace the values in your .env with your Supabase credentials:

```bash
# Database (Supabase)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Supabase Configuration
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_SERVICE_KEY=[YOUR-SERVICE-KEY]
SUPABASE_STORAGE_BUCKET=documents
```

## Step 4: Run This Setup Script

After updating your .env file with Supabase credentials, run:

```bash
# Install dependencies (if not already done)
poetry install --no-root

# Run database migrations
poetry run alembic upgrade head

# Start the backend
poetry run uvicorn app.main:app --reload
```

## Troubleshooting

### Connection Issues
- Make sure your IP is whitelisted in Supabase (Settings > Database > Connection pooling)
- Verify the DATABASE_URL format is correct
- Check that you're using the correct password from Supabase

### Migration Issues
- If migrations fail, check the Supabase SQL Editor to see if tables already exist
- You can reset with: `poetry run alembic downgrade base` then `poetry run alembic upgrade head`

### Storage Issues
- Ensure the `documents` bucket exists and is set to private
- Verify SUPABASE_SERVICE_KEY is the service role key, not the anon key