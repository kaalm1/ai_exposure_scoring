# AI Exposure Scoring API

FastAPI + SQLAlchemy (async) + Alembic project for managing AI exposure scoring.

---

## 🚀 Quickstart

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-org/ai_exposure_scoring.git
cd ai_exposure_scoring
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` → `.env` and update values:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_exposure
```

The database and user will be auto-created at app startup if they don't exist.

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000

---

## 📦 Database Management

We use Alembic for migrations.

### Create a new migration

```bash
alembic  -c app/alembic.ini revision --autogenerate -m "create initial tables"
```

This will generate a migration script in `app/alembic/versions/`.

### Apply migrations

```bash
alembic  -c app/alembic.ini upgrade head
```

The application also runs pending migrations automatically on startup.

### Downgrade migrations (undo)

```bash
alembic  -c app/alembic.ini downgrade -1
```

---

## 🛠️ Useful Commands

### Check current DB version

```bash
alembic current
```

### View history

```bash
alembic history --verbose
```

### Stamp database without running migrations

```bash
alembic stamp head
```

---

## 📚 API Documentation

Once the server is running, visit:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

---

## 🏗️ Project Structure

```
ai_exposure_scoring/
├── app/
│   ├── alembic/           # Database migrations
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # API endpoints
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── main.py            # FastAPI application
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
└── README.md
```

---

## 🐛 Troubleshooting

### Database connection issues

- Ensure PostgreSQL is running
- Verify credentials in `.env`
- Check that the database exists (auto-created on first run)

### Migration conflicts

```bash
# Reset to a specific version
alembic  -c app/alembic.ini downgrade <revision>

# Re-run migrations
alembic -c app/alembic.ini upgrade head
```

---

## 📄 License

[Add your license here]

---

## 🤝 Contributing

[Add contribution guidelines here]