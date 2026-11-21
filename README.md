# ResumeForge AI

**Beat the ATS. Land the interview.** — An AI-powered job application copilot.

ResumeForge AI analyzes your resume against a job description, returns an ATS match score with keyword gaps, rewrites your resume to be ATS-optimized, generates a tailored cover letter, and prepares interview questions with suggested answers.

## Business overview

### Problem
75% of resumes are rejected by Applicant Tracking Systems before a human ever reads them. Job seekers spend hours tailoring resumes manually and still miss keywords. Existing tools (Jobscan, Teal, Resume.io) charge $20–$50/month and most are clunky.

### Target audience
- Active job seekers (tech, finance, marketing, new grads)
- Career coaches and resume writers (B2B)
- University career centers

### Monetization strategy
- **Freemium**: 3 free optimizations/month (with analysis + tailored resume + cover letter)
- **Premium $19/month or $149/year**: unlimited optimizations, AI interview prep, PDF & DOCX export, priority support
- **B2B tier $99/month**: team seats, white-label, API access for career coaches
- Low operating cost: one Groq LLM call per optimization (~$0.001–$0.005), SQLite, no heavy infra. Margin > 90%.

### Competitive advantage
- Faster (Groq inference) and cheaper to operate than incumbents
- All-in-one: score + rewrite + cover letter + interview prep
- Self-hostable, easy to white-label and sell

## Tech stack
- Backend: FastAPI (Python), SQLAlchemy, SQLite
- AI: Groq (openai/gpt-oss-120b) — swap provider via env
- Auth: JWT + bcrypt
- Frontend: Vanilla JS + Tailwind v4 (browser build), served by FastAPI
- Exports: reportlab (PDF), python-docx (DOCX)

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env   # then edit GROQ_API_KEY, JWT_SECRET

# 3. Run
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 4. Open
http://localhost:8000
```

### Environment variables
| Var | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key (free at console.groq.com) |
| `GROQ_MODEL` | Model for heavy tasks (default openai/gpt-oss-120b) |
| `JWT_SECRET` | Secret for signing auth tokens |
| `DATABASE_URL` | SQLAlchemy URL (default sqlite:///./data/app.db) |
| `FREE_MONTHLY_LIMIT` | Free tier monthly optimizations (default 3) |
| `STRIPE_SECRET_KEY` | Optional, for real payments |
| `STRIPE_PRICE_ID` | Optional Stripe price id |
| `STRIPE_WEBHOOK_SECRET` | Optional Stripe webhook secret |

## Stripe (optional)
Set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET` in `.env` and restart. The `/api/billing/checkout` endpoint creates a real Checkout Session. Without these, the app runs in demo mode with a one-click upgrade.

## API
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/resumes`, `POST /api/resumes/upload`, `GET /api/resumes`, `GET /api/resumes/{id}`, `DELETE /api/resumes/{id}`
- `POST /api/job-descriptions`, `GET /api/job-descriptions`, `GET /api/job-descriptions/{id}`
- `POST /api/optimize` — main AI endpoint
- `GET /api/optimizations`, `GET /api/optimizations/{id}`, `DELETE /api/optimizations/{id}`
- `GET /api/usage`
- `POST /api/billing/demo-upgrade`, `POST /api/billing/checkout`, `POST /api/billing/webhook`
- `GET /api/export/{id}/pdf`, `GET /api/export/{id}/docx`

## License
Proprietary — all rights reserved. Built to be sold.
"# resumeforge-ai" 
"# resumeforge-ai" 
