# BusinessAgent

A multi-tenant AI agent platform that gives businesses a central interface to manage email, calendars, and spreadsheets via a conversational AI assistant powered by Claude.

---

## Project Structure

```
BusinessAgent/
├── ai-agent-backend/       FastAPI backend (Python)
└── ai-agent-frontend/      Next.js frontend (TypeScript)
```

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- A [Supabase](https://supabase.com) account
- An [Anthropic](https://console.anthropic.com) API key
- An [Upstash](https://upstash.com) Redis database
- A [Google Cloud](https://console.cloud.google.com) project with Gmail, Calendar, and Sheets APIs enabled
- A [Microsoft Azure](https://portal.azure.com) app registration with Mail, Calendar, and Files permissions

---

## Backend Setup (`ai-agent-backend`)

### 1. Clone and create virtual environment

```powershell
cd ai-agent-backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in all values:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

TOKEN_ENCRYPTION_KEY=...   # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

ANTHROPIC_API_KEY=...

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback

FRONTEND_URL=http://localhost:3000
REDIS_URL=rediss://default:password@your-endpoint.upstash.io:6379
```

### 3. Set up the database

In your Supabase dashboard, go to **SQL Editor** and run the contents of `schema.sql`. This creates all tables, enums, RLS policies, and seeds the plan limits.

### 4. Create your first tenant and user

After running the schema, run this in the Supabase SQL Editor:

```sql
-- Create a tenant
insert into tenants (name, slug, plan)
values ('My Business', 'my-business', 'pro')
returning id;

-- After signing up via the frontend, insert the user row
-- Replace both UUIDs with your actual values
insert into users (id, tenant_id, email, role)
values (
  'auth-user-uuid-from-supabase',
  'tenant-uuid-from-above',
  'you@email.com',
  'admin'
);
```

### 5. Run the backend

```powershell
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`

---

## Frontend Setup (`ai-agent-frontend`)

### 1. Install dependencies

```powershell
cd ai-agent-frontend
npm install
```

### 2. Configure environment variables

Create `.env.local` in the frontend root:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. Run the frontend

```powershell
npm run dev
```

---

## Pages

| URL | Description |
|-----|-------------|
| `http://localhost:3000` | Login / signup |
| `http://localhost:3000/chat` | Main agent chat interface |
| `http://localhost:3000/admin` | Agent configuration dashboard |

---

## Connecting Google / Microsoft Accounts

Once logged in, connect provider accounts by visiting these backend endpoints directly in the browser (while logged in):

- **Google:** `http://localhost:8000/auth/google/connect`
- **Microsoft:** `http://localhost:8000/auth/microsoft/connect`

Both will redirect through the provider's OAuth consent screen and store tokens automatically.

---

## Backend File Structure

```
ai-agent-backend/
├── main.py                     Entry point, router registration, CORS
├── schema.sql                  Supabase database schema
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── agent_core.py           Claude streaming loop + tool use handler
│   └── memory.py               Long-term memory summarization
│
├── tools/
│   ├── registry.py             Tool definitions and routing
│   ├── gmail.py                Gmail read/send
│   ├── gcal.py                 Google Calendar read/create
│   ├── sheets.py               Google Sheets read/write
│   ├── outlook.py              Outlook read/send
│   ├── outlook_calendar.py     Outlook Calendar read/create
│   └── excel.py                Excel read/write (OneDrive)
│
├── middleware/
│   └── rate_limiter.py         Per-tenant Redis usage counters
│
├── oauth_router.py             Google + Microsoft OAuth flows
├── chat_router.py              SSE streaming chat endpoint
├── admin_router.py             Agent config CRUD
├── memory_router.py            Memory inspection + management
├── usage_router.py             Billing usage stats
├── token_service.py            Encrypted OAuth token storage + refresh
└── dependencies.py             JWT auth middleware
```

---

## Deployment

### Backend — Railway

1. Push `ai-agent-backend` to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all environment variables from `.env` in the Railway dashboard
4. Railway auto-detects the Python app and deploys it
5. Copy the generated Railway URL and update `FRONTEND_URL` in your env vars and `GOOGLE_REDIRECT_URI` / `MICROSOFT_REDIRECT_URI` to use the Railway URL

### Frontend — Vercel

1. Push `ai-agent-frontend` to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
3. Add environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` = your Railway backend URL
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy — Vercel handles the rest

### After deploying

Update the following to use your production URLs:

- `FRONTEND_URL` in backend env vars → Vercel URL
- `GOOGLE_REDIRECT_URI` → `https://your-railway-url/auth/google/callback`
- `MICROSOFT_REDIRECT_URI` → `https://your-railway-url/auth/microsoft/callback`
- In Google Cloud Console → update **Authorized redirect URIs**
- In Azure Portal → update **Redirect URI**
- In Supabase → **Authentication → URL Configuration** → add your Vercel URL

---

## Plan Limits

Defined in the `plan_limits` table. Default values:

| Plan | Claude Calls/mo | Tool Calls/mo | Max Users |
|------|----------------|---------------|-----------|
| Free | 100 | 200 | 2 |
| Pro | 2,000 | 5,000 | 10 |
| Enterprise | Unlimited | Unlimited | Unlimited |

To change a tenant's plan:

```sql
update tenants set plan = 'pro' where slug = 'my-business';
```

---

## Common Issues

**`AttributeError: 'NoneType' object has no attribute 'data'`**
A `maybe_single()` query returned no rows. Ensure the tenant and user rows exist in the database.

**`supabase_url is required`**
The `.env` file is not loading. Make sure `load_dotenv()` is called at the top of the file and that `.env` exists with no quotes around values.

**Redis authentication error**
Check that `REDIS_URL` in `.env` has no surrounding quotes and uses the full `rediss://` URL from Upstash including the password.

**Anthropic 400 credit balance error**
Add credits at [console.anthropic.com](https://console.anthropic.com) → Plans & Billing.
