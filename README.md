# 🎓 Google Classroom Smart Assistant

AI-powered classroom management with RAG-based Q&A, analytics, and Google Classroom integration.

## ✨ Features

- **📚 Google Classroom Sync** - Auto-import courses, assignments, submissions
- **🤖 AI Q&A** - Ask questions, get source-backed answers with confidence scores
- **📊 Analytics** - Rule-based, explainable performance insights
- **⏰ Reminders** - Smart multi-level deadline notifications
- **📋 Reports** - Weekly/monthly reports with CSV export

## 🚀 Quick Start

```bash
# Start everything with Docker
docker-compose up -d

# Or run manually:
# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## 🔧 Configuration

Copy `.env.example` to `.env` in both `backend/` and `frontend/`:

```env
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/classroom
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
JWT_SECRET_KEY=your-secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1
```

## 📡 API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/google` | GET | Start OAuth |
| `/api/v1/courses/sync` | POST | Sync Google Classroom |
| `/api/v1/qa` | POST | Ask AI |
| `/api/v1/analytics/my-performance` | GET | Performance data |

## 🛠 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, ChromaDB
- **Frontend**: Next.js 14, TailwindCSS, Recharts
- **AI**: sentence-transformers, RAG pipeline

## 📁 Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/       # REST endpoints
│   │   ├── core/         # Auth, security
│   │   ├── models/       # DB models
│   │   ├── services/     # Business logic
│   │   └── integrations/ # External APIs
│   └── requirements.txt
└── frontend/
    └── src/app/          # Next.js pages
```

---

Built with ❤️ for educators
