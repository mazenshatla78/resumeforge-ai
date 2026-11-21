# Netlify Deployment Guide — ResumeForge AI

## Architecture
- **Frontend**: Hosted on Netlify (static files from `frontend/`)
- **Backend**: Hosted on Railway/Render/Fly.io (FastAPI + Python)
- **Database**: PostgreSQL (Supabase/Neon/Railway)
- **AI**: Groq API (external, no hosting needed)

## Step 1: Deploy Backend
1. Push code to GitHub
2. Create a new service on Railway/Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variables (from .env.example):
   - `GROQ_API_KEY`
   - `JWT_SECRET` (generate a strong random string)
   - `DATABASE_URL` (PostgreSQL connection string)
   - `ALLOWED_ORIGINS` (your Netlify URL)
   - `APP_BASE_URL` (your Netlify URL)
6. Note your backend URL (e.g., https://resumeforge-api.railway.app)

## Step 2: Deploy Frontend to Netlify
1. Connect your GitHub repo to Netlify
2. Set publish directory: `frontend`
3. Set build command: (none — static files)
4. In Netlify dashboard, set environment variable:
   - `API_BASE_URL` = your backend URL (e.g., https://resumeforge-api.railway.app)
5. Or edit `frontend/config.js` to set `window.API_BASE_URL = "https://your-backend-url.com"`
6. Deploy

## Step 3: Configure CORS
In your backend `.env`:
```
ALLOWED_ORIGINS=https://your-site.netlify.app
APP_BASE_URL=https://your-site.netlify.app
```

## Step 4: Database
- Use Supabase/Neon/Railway PostgreSQL
- Set `DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname`
- Tables auto-create on startup

## Step 5: Tailwind Build (optional)
- The app uses Tailwind v4 browser build (works offline)
- For optimized builds, install tailwindcss CLI and run: `tailwindcss -i frontend/input.css -o frontend/output.css --minify`
- Requires npm access (may be blocked by corporate proxy)

## Free Tier Limits
- Netlify: 100GB bandwidth/month, 300 build minutes/month
- Railway: $5 free credit/month (limited hours)
- Render: 750 hours/month free (sleeps after 15min inactivity)
- Supabase: 500MB database, 2GB bandwidth
- Groq: free tier with rate limits

## Notes
- Video generation (Remotion + Three.js) runs on YOUR device, not on the server
- The website (ResumeForge AI) is hosted; video creation is local
- When you want a video, tell me and I'll render it locally on your device