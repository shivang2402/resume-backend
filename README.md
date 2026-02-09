# Resume Forge — Backend API

> Modular resume generation with flavor-based versioning and AI-powered job matching

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)

---

## Overview

Resume Forge Backend is a FastAPI-powered REST API for managing modular resume content with intelligent versioning. Instead of maintaining separate resume documents for different job types, users create **sections** with **flavors** — enabling the same experience (e.g., an Amazon internship) to be tailored for systems engineering, full-stack, ML, or SRE roles.

The platform supports complete resume lifecycle management: content creation with automatic tagging, AI-powered job description matching, PDF generation via LaTeX compilation, application tracking, and cold outreach message generation.

**Key differentiator:** A multi-dimensional indexing system where sections are addressed as `type:key:flavor:version` (e.g., `experience:amazon:systems:1.2`). Updates automatically increment version numbers using semantic versioning, preserving history while always tracking the "current" version.

---

## Architecture

The backend follows a clean layered architecture:

```
┌─────────────────────────────────────────────────────┐
│                    Routers (API Layer)               │
│   auth, sections, applications, generate, outreach   │
│      jd_matcher, section_configs, ai                 │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                 Services (Business Logic)            │
│  section_service, generator_service, gemini_service  │
│  jd_matcher_service, outreach_service, tag_generator │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  Models (Database Layer)             │
│     User, Section, Application, SectionConfig        │
│   OutreachThread, OutreachMessage, OutreachTemplate  │
└─────────────────────────────────────────────────────┘
```

- **Routers:** Define HTTP endpoints, handle request/response validation via Pydantic schemas
- **Services:** Contain business logic, database operations, AI integrations
- **Models:** SQLAlchemy ORM models representing PostgreSQL tables

---

## Core Concepts

### Sections & Flavors

Sections are indexed using four dimensions:

| Dimension | Description | Examples |
|-----------|-------------|----------|
| `type` | The category of content | `experience`, `project`, `skills`, `education`, `heading`, `location`, `email` |
| `key` | Unique identifier within the type | `amazon`, `kambaz`, `memory_allocator`, `default` |
| `flavor` | Variation targeting specific roles | `systems`, `fullstack`, `ml`, `sre`, `default` |
| `version` | Semantic version number | `1.0`, `1.1`, `2.0` |

**Example addressing:** `experience:amazon:systems:1.2` refers to the Amazon experience section, systems-focused flavor, version 1.2.

### Auto-Versioning

When you update a section, the system:
1. Marks the current version as `is_current = false`
2. Creates a new version with incremented minor version (`1.0` → `1.1`)
3. Sets the new version as `is_current = true`

All historical versions are preserved and queryable.

### Section Types

| Type | Purpose | Content Fields |
|------|---------|----------------|
| `experience` | Work experience entries | `title`, `company`, `location`, `dates`, `bullets` |
| `project` | Personal/academic projects | `name`, `tech`, `bullets` |
| `skills` | Technical skills by category | Dict of category → skills list |
| `education` | Degree information | `degree`, `institution`, `dates`, `gpa` |
| `heading` | Contact/header information | `name`, `phone`, `email`, `linkedin`, `github` |
| `location` | Location override | `value` (city, state) |
| `email` | Email override | `value` |

---

## API Reference

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sync` | Sync user from OAuth callback (creates or updates) |
| `GET` | `/me` | Get current user by `X-User-Id` header |

### Sections (`/api/sections`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all sections for user |
| `GET` | `/{type}` | List sections filtered by type |
| `GET` | `/{type}/{key}/{flavor}` | Get all versions of a section |
| `GET` | `/{type}/{key}/{flavor}/{version}` | Get specific version |
| `POST` | `/` | Create new section (auto-generates tags if Gemini key provided) |
| `POST` | `/bulk` | Bulk create multiple sections |
| `PUT` | `/{type}/{key}/{flavor}` | Update section (creates new version) |
| `DELETE` | `/{type}/{key}/{flavor}/{version}` | Delete specific version |

### Applications (`/api/applications`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all applications (optional `?status=` filter) |
| `GET` | `/{id}` | Get single application |
| `POST` | `/` | Create new application |
| `PUT` | `/{id}` | Update application status/notes |
| `DELETE` | `/{id}` | Delete application |

### PDF Generation (`/api/generate`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Generate PDF resume (returns file download) |
| `POST` | `/preview` | Generate PDF and return as base64 |

### JD Matcher (`/api/jd`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Analyze job description, suggest matching sections |
| `POST` | `/recalculate-keywords` | Recalculate missing keywords for current selection |

### Outreach (`/api/outreach`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/templates` | List all message templates |
| `POST` | `/templates` | Create template |
| `GET` | `/templates/{id}` | Get single template |
| `PUT` | `/templates/{id}` | Update template |
| `DELETE` | `/templates/{id}` | Delete template |
| `GET` | `/threads` | List conversation threads |
| `POST` | `/threads` | Create thread |
| `GET` | `/threads/{id}` | Get thread with details |
| `PUT` | `/threads/{id}` | Update thread |
| `DELETE` | `/threads/{id}` | Delete thread and messages |
| `GET` | `/threads/{id}/messages` | List messages in thread |
| `POST` | `/threads/{id}/messages` | Add message to thread |
| `DELETE` | `/threads/{id}/messages/{msg_id}` | Delete specific message |
| `POST` | `/generate` | AI-generate outreach message |
| `POST` | `/refine` | Refine message with instructions |
| `POST` | `/parse-conversation` | Parse raw conversation into messages |
| `POST` | `/generate-reply` | Generate reply for thread |

### Section Configs (`/api/section-configs`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all section configs |
| `GET` | `/{type}/{key}` | Get config for specific section |
| `PUT` | `/{type}/{key}` | Upsert section priority config |
| `DELETE` | `/{type}/{key}` | Reset to default priority |

### AI (`/api/ai`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/test` | Test Gemini API connection |
| `GET` | `/health` | AI service health check |

---

## Database Models

### User
Stores OAuth user information.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `email` | String | Unique email address |
| `name` | String | Display name |
| `avatar_url` | String | Profile picture URL |
| `provider` | String | OAuth provider (google, github) |
| `provider_id` | String | Provider's user ID |

### Section
Resume content sections with versioning.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key to users |
| `type` | String | Section type |
| `key` | String | Section identifier |
| `flavor` | String | Role-specific variation |
| `version` | String | Semantic version |
| `content` | JSONB | Flexible content storage |
| `is_current` | Boolean | Whether this is the active version |

**Unique constraint:** (`user_id`, `type`, `key`, `flavor`, `version`)

### Application
Job application tracking.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key to users |
| `company` | String | Company name |
| `role` | String | Job title |
| `status` | String | `applied`, `phone_screen`, `technical`, `onsite`, `offer`, `rejected` |
| `resume_config` | JSONB | Section references used for this application |
| `job_description` | Text | Full JD text |
| `applied_at` | Date | Application date |

### SectionConfig
Per-section priority settings for JD matching.

| Field | Type | Description |
|-------|------|-------------|
| `section_type` | String | Type of section |
| `section_key` | String | Section identifier |
| `priority` | String | `always`, `normal`, `never` |
| `fixed_flavor` | String | Required flavor when priority is `always` |

### OutreachThread, OutreachMessage, OutreachTemplate
Cold outreach conversation management.

---

## AI Features

### BYOK (Bring Your Own Key)

Users provide their own Google Gemini API key via the `X-Gemini-API-Key` header. The backend never stores API keys — they're passed per-request for all AI features.

### JD Matcher

1. **Extract JD Terms:** AI extracts key requirements, technologies, and skills from the job description
2. **Tag-Based Matching:** Sections have pre-computed tags (generated on create/update). The matcher compares JD terms against section tags
3. **Suggestions:** Returns recommended sections + flavors, respecting user's priority configs (always/never include certain sections)
4. **Missing Keywords:** Identifies JD keywords not covered by selected sections

### Cold Outreach

- **Message Generation:** Create personalized networking messages based on company, contact, and resume context
- **Message Refinement:** Iteratively improve messages with natural language instructions
- **Conversation Parsing:** Parse pasted conversation dumps into structured sent/received messages
- **Reply Generation:** AI-generate contextual replies for ongoing threads

### Tag Generation

When sections are created or updated (with Gemini key provided), the system auto-generates tags including:
- Technical skills (languages, frameworks, tools)
- Soft skills (leadership, communication)
- Impact keywords (scaled, optimized, led)
- Domain terms (distributed systems, microservices)
- Metrics indicators (40% latency reduction, 1M users)

---

## PDF Generation Pipeline

### Overview

```
Section Selection → LaTeX Rendering → pdflatex Compilation → PDF Output
```

### Template Structure

```
templates/
├── resume.tex           # Main document (includes sections)
├── custom-commands.tex  # LaTeX macros for resume formatting
└── src/
    ├── heading.tex      # Contact information
    ├── education.tex    # Education section
    ├── experience.tex   # Work experience
    ├── projects.tex     # Projects section
    └── skills.tex       # Skills table
```

### Flow

1. **Section Selection:** Frontend sends `resume_config` specifying which sections/flavors to include
2. **Content Fetching:** Service fetches section content from database
3. **LaTeX Generation:** Python generates `.tex` files from section content, escaping special characters
4. **Compilation:** `pdflatex` runs twice (for cross-references) in a temp directory
5. **Output:** PDF bytes returned as download or base64

---

## Project Structure

```
resume-backend/
├── app/
│   ├── main.py              # FastAPI app initialization, CORS, router mounting
│   ├── config.py            # Pydantic Settings for environment variables
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── section.py       # Section model with versioning
│   │   ├── application.py   # Application tracking model
│   │   ├── section_config.py # Priority configuration model
│   │   ├── outreach_thread.py    # Conversation thread model
│   │   ├── outreach_message.py   # Individual message model
│   │   └── outreach_template.py  # Saved message templates
│   ├── routers/
│   │   ├── auth.py          # OAuth sync endpoints
│   │   ├── sections.py      # CRUD with auto-tagging
│   │   ├── applications.py  # Application tracking
│   │   ├── generate.py      # PDF generation
│   │   ├── jd_matcher.py    # Job description analysis
│   │   ├── outreach.py      # Cold outreach management
│   │   ├── section_configs.py # Priority settings
│   │   └── ai.py            # Gemini test endpoints
│   ├── schemas/
│   │   ├── user.py          # User Pydantic schemas
│   │   ├── section.py       # Section create/update/response
│   │   ├── application.py   # Application schemas
│   │   ├── section_config.py # Config schemas
│   │   ├── jd_matcher.py    # JD analysis request/response
│   │   └── outreach.py      # Outreach schemas with enums
│   ├── services/
│   │   ├── user_service.py       # User sync logic
│   │   ├── section_service.py    # Section CRUD + versioning
│   │   ├── application_service.py # Application CRUD
│   │   ├── generator_service.py  # LaTeX/PDF generation
│   │   ├── gemini_service.py     # Google Gemini AI client
│   │   ├── jd_extractor.py       # Extract terms from JD
│   │   ├── jd_matcher_service.py # Match sections to JD
│   │   ├── keyword_service.py    # Missing keyword detection
│   │   ├── tag_generator.py      # Auto-tag section content
│   │   ├── outreach_service.py   # Outreach CRUD operations
│   │   └── ai_outreach_service.py # AI message generation
│   └── utils/
│       └── latex.py         # LaTeX generation utilities
├── templates/
│   ├── resume.tex           # Main LaTeX template
│   ├── custom-commands.tex  # LaTeX macros
│   └── src/                 # Section templates
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- MacTeX or TeX Live (for `pdflatex`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/resume-backend.git
   cd resume-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database:**
   ```bash
   psql -U postgres
   CREATE DATABASE resume_forge;
   CREATE USER resume_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE resume_forge TO resume_user;
   \q
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. **Access API docs:** http://localhost:8000/docs

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://resume_user:password@localhost:5432/resume_forge` |
| `SECRET_KEY` | JWT signing key (for production auth) | `your-super-secret-key-min-32-chars` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:3000,https://yourdomain.com` |

---

## Example API Calls

### Create a Section

```bash
curl -X POST http://localhost:8000/api/sections \
  -H "Content-Type: application/json" \
  -H "X-User-Id: your-user-uuid" \
  -H "X-Gemini-API-Key: your-gemini-key" \
  -d '{
    "type": "experience",
    "key": "amazon",
    "flavor": "systems",
    "content": {
      "title": "Software Development Engineer Intern",
      "company": "Amazon",
      "location": "Seattle, WA",
      "dates": "May 2024 - Aug 2024",
      "bullets": [
        "Designed and implemented a distributed caching layer reducing API latency by 40%",
        "Built real-time monitoring dashboard using CloudWatch and Lambda"
      ]
    }
  }'
```

### List Sections by Type

```bash
curl http://localhost:8000/api/sections/experience \
  -H "X-User-Id: your-user-uuid"
```

### Generate PDF Resume

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "X-User-Id: your-user-uuid" \
  -o resume.pdf \
  -d '{
    "resume_config": {
      "experiences": ["amazon:systems:1.0", "google:fullstack:1.2"],
      "projects": ["kambaz:fullstack:1.0"],
      "skills": "systems:1.0",
      "education": "default:1.0"
    }
  }'
```

### Log an Application

```bash
curl -X POST http://localhost:8000/api/applications \
  -H "Content-Type: application/json" \
  -H "X-User-Id: your-user-uuid" \
  -d '{
    "company": "Stripe",
    "role": "Backend Engineer",
    "job_url": "https://stripe.com/jobs/123",
    "location": "San Francisco, CA",
    "resume_config": {
      "experiences": ["amazon:systems:1.0"],
      "projects": ["payment_api:fullstack:1.0"],
      "skills": "fullstack:1.0"
    },
    "applied_at": "2024-01-15"
  }'
```

### Analyze Job Description

```bash
curl -X POST http://localhost:8000/api/jd/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-Id: your-user-uuid" \
  -H "X-Gemini-API-Key: your-gemini-key" \
  -d '{
    "job_description": "We are looking for a backend engineer with experience in distributed systems, Python, and AWS..."
  }'
```

---

## License

MIT