# NeuronLab Backend

FastAPI backend for the NeuronLab ML learning platform - an interactive platform for learning machine learning through hands-on coding exercises.

## Features

- **Problem API** - Fetch ML problems from database with filtering
- **Quest System** - AI-generated learning paths with interactive exercises
- **Code Execution** - Secure sandboxed Python code execution
- **AI Hints** - GPT-powered hints for debugging assistance
- **Solution Generation** - AI-generated solutions with explanations
- **Math Sample Generator** - Generate worked math examples for formulas
- **Authentication** - JWT-based user authentication
- **Progress Tracking** - Track user submissions and quest progress

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Development database (PostgreSQL for production)
- **Docker** - Sandboxed code execution
- **OpenAI API** - AI-powered features

## Getting Started

### Prerequisites

- Python 3.10+
- Docker (for code execution sandbox)
- OpenAI API key (or GitHub Copilot with API access)

> **Note:** AI-powered features (hints, solutions, quest generation, math examples) require an OpenAI API key or GitHub Copilot installed on your system with API access enabled.

### Installation

```bash
# Clone the repository
git clone https://github.com/NeuronLab-ID/backend.git
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

Create a `.env` file with:

```env
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
DATABASE_URL=sqlite:///./deepml.db
PROBLEMS_DIR=d:/PythonProject/deepml/problems
QUESTS_DIR=d:/PythonProject/deepml/quests
```

### Database Setup

```bash
# Seed problems and quests from JSON files
python seed_problems.py
```

## Data Management

### Database Schema

The backend uses SQLite with the following main tables:

| Table | Description |
|-------|-------------|
| `users` | User accounts and authentication |
| `problems` | ML problem definitions (270 problems) |
| `quests` | AI-generated learning quests |
| `quest_progress` | User progress on quest steps |
| `submissions` | User code submissions |
| `problem_solutions` | Cached AI-generated solutions |

### Problem & Quest Data Sources

Problems and quests can come from two sources:

1. **JSON Files** (Primary source at `PROBLEMS_DIR` and `QUESTS_DIR`)
   - `problems/problem_XXXX.json` - Problem definitions
   - `quests/quest_XXXX.json` - Pre-generated quests

2. **SQLite Database** (Runtime cache)
   - Faster queries than file I/O
   - Required for production deployment

### Seeding the Database

The `seed_problems.py` script imports all problems and quests from JSON files:

```bash
# Full import (270 problems, ~159 quests)
python seed_problems.py

# What it does:
# 1. Reads all problem_*.json files from PROBLEMS_DIR
# 2. Reads all quest_*.json files from QUESTS_DIR  
# 3. Creates Problem and Quest records in database
# 4. Handles Base64 encoded fields (description, learn_section)
# 5. Skips duplicates on re-run
```

### Quest Generator

Quests are AI-generated learning paths created by the separate `quest_generator.py` tool:

```bash
# Located in the deepml project (not this backend)
cd d:/PythonProject/deepml

# Generate quest for a single problem
python quest_generator.py --problem-id 1

# Generate quests by category
python quest_generator.py --category "Linear Algebra"

# Generate all missing quests
python quest_generator.py --all

# Retry failed quests
python quest_generator.py --retry-failed

# List failed quests
python quest_generator.py --list-failed
```

**Quest Generation Features:**
- Uses GPT-4 to create 5-step learning paths
- Each step includes theory, formulas, and practice exercises
- Generates test cases for code exercises
- Saves to JSON files and optionally to database
- Tracks failures in `failed_quests.json`

### On-Demand Quest Generation

The backend can generate quests on-the-fly if not found:

```bash
# API endpoint with generate flag
GET /api/quests/1?generate=true

# This will:
# 1. Check database cache
# 2. Check JSON files
# 3. If not found, run quest_generator.py as subprocess (~60s)
# 4. Cache result in database
```

> **Note:** On-demand generation is slow (~60 seconds) and requires OpenAI API credits.

### Migrating Data

To migrate problems/quests to a new database:

```bash
# 1. Export from source (JSON files already exist)
# 2. Copy JSON files to new server
# 3. Set PROBLEMS_DIR and QUESTS_DIR in .env
# 4. Run seeder
python seed_problems.py
```

### Running the Server

```bash
# Development
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/problems` | List all problems (paginated) |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |

### Protected Endpoints (Require Authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/problems/{id}` | Get problem details |
| GET | `/api/problems/{id}/solution` | Get AI-generated solution |
| GET | `/api/quests/{id}` | Get quest for problem |
| POST | `/api/execute` | Execute Python code |
| POST | `/api/hint` | Get AI debugging hint |
| POST | `/api/generate-sample` | Generate math example |
| GET | `/api/users/me` | Get current user profile |
| GET | `/api/users/progress` | Get user progress stats |

### Authentication

Include JWT token in Authorization header:
```
Authorization: Bearer <token>
```

## Project Structure

```
backend/
├── app/
│   ├── models/
│   │   ├── db.py          # SQLAlchemy models
│   │   └── schemas.py     # Pydantic schemas
│   ├── routes/
│   │   ├── auth.py        # Authentication routes
│   │   ├── problems.py    # Problem CRUD
│   │   ├── quests.py      # Quest routes
│   │   ├── execution.py   # Code execution
│   │   ├── hints.py       # AI hints
│   │   └── math_samples.py # Math examples
│   ├── services/
│   │   ├── executor.py    # Docker sandbox
│   │   ├── hint_generator.py
│   │   ├── solution_generator.py
│   │   └── quest_service.py
│   ├── config.py          # Configuration
│   └── database.py        # DB connection
├── sandbox/
│   ├── Dockerfile         # Sandbox image
│   └── runner.py          # Code runner
├── main.py                # Application entry
├── seed_problems.py       # Database seeder
└── requirements.txt
```

## Docker Sandbox

Build the sandbox image for secure code execution:

```bash
cd sandbox
docker build -t neuronlab-sandbox .
```

## Development

### Running Tests

```bash
pytest
```

### API Documentation

FastAPI auto-generates OpenAPI docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT License - See [LICENSE](LICENSE) for details.
