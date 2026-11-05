# Nettle Basic

A simplified version of the Nettle risk engineering platform. This app allows risk engineers to manage clients, create assessments, upload evidence, and generate AI-powered risk reports.

## Quick Start

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key

docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin/

The database is seeded with sample clients, assessments, and evidence on first run.

## Architecture

- **Backend**: Django + Django REST Framework (Python 3.11)
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Database**: PostgreSQL 15
- **AI**: Anthropic Claude API for report generation

## API Endpoints

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/portfolio/clients/` | GET, POST | List/create clients |
| `/api/portfolio/clients/:id/` | GET, PUT, PATCH, DELETE | Client detail |
| `/api/assessments/` | GET, POST | List/create assessments |
| `/api/assessments/:id/` | GET, PUT, PATCH, DELETE | Assessment detail |
| `/api/evidence/` | GET, POST | List/create evidence |
| `/api/evidence/?assessment=:id` | GET | Evidence for an assessment |
| `/api/reports/` | GET, POST | List/create reports |
| `/api/reports/:id/generate/` | POST | Generate report (SSE stream) |
