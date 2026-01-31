# Resume Forge - Backend

Backend API for Resume Forge - A resume generation and application tracking system.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **PDF Generation:** pdflatex

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- pdflatex (texlive)

### Installation

1. Clone the repository:
```bash
   git clone https://github.com/YOUR_USERNAME/resume-backend.git
   cd resume-backend
```

2. Create virtual environment:
```bash
   python -m venv venv
   source venv/bin/activate
```

3. Install dependencies:
```bash
   pip install -r requirements.txt
```

4. Set up environment variables:
```bash
   cp .env.example .env
```

5. Run the server:
```bash
   uvicorn app.main:app --reload
```

## API Documentation

http://localhost:8000/docs

## License

MIT