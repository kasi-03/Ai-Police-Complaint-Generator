# Voice-Based AI-Assisted Police Complaint Drafting System

A Flask-based web application that helps police personnel draft complaints from voice narrations using AI. Deployed and validated at Duvvada Police Station, Visakhapatnam.

## Features

- 🎙️ **Voice Recording & Upload** - Live browser recording or audio file upload
- 🤖 **AI-Powered Transcription** - Google Speech Recognition (Telugu) + Groq Whisper fallback
- 📝 **Smart Complaint Generation** - LLM converts narration to formal FIR format (Telugu + English)
- 📄 **Bilingual PDF Export** - Professional PDFs in Telugu and English with proper formatting
- 🗂️ **Digital Case Management** - Organized case folders with audio, transcripts, and PDFs
- 🔍 **Search & Dashboard** - Filter complaints by ID, name, phone, subject
- ⚙️ **Station Configuration** - Customizable police station details in English & Telugu
- 🔒 **Production Ready** - Docker, health checks, security headers, rate limiting, Redis caching
- ⚡ **Performance Optimized** - Redis caching for complaints and statistics

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0, Gunicorn |
| AI/ML | Groq API (Whisper + Llama-3), Google Speech Recognition |
| PDF Generation | Playwright (Chromium headless) |
| Audio Processing | pydub, SpeechRecognition |
| Database | SQLite (local) / PostgreSQL (production) |
| Caching | Redis 7 (with LRU eviction) |
| Security | Flask-Limiter, Flask-Talisman, Flask-CORS |
| Deployment | Docker, Docker Compose, Render, Railway, Fly.io |
| CI/CD | GitHub Actions |

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- ffmpeg (for audio conversion)
- Groq API Key ([get one free](https://console.groq.com/keys))

### Installation

```bash
# Clone and enter directory
cd CSP_V2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy environment template and add your API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run the application
python app.py
```

Visit `http://localhost:5000`

## Docker Deployment (Recommended)

### Local Docker

```bash
# Build and run (includes Redis)
docker-compose up --build

# Or with production profile (includes nginx)
docker-compose --profile production up --build
```

Visit `http://localhost:5000` (app) - Redis runs on `localhost:6379`

The `docker-compose.yml` includes:
- **app** - Flask application with Gunicorn (4 workers)
- **redis** - Redis 7 Alpine with persistence and LRU eviction

### Production Deployment Options

#### Option 1: Render (Free Tier Available)

1. Push code to GitHub
2. Connect repo at [render.com](https://render.com)
3. Use `render.yaml` for auto-configuration
4. Add `GROQ_API_KEY` in Environment Variables
5. Deploy!

#### Option 2: Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Option 3: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch
fly launch
fly deploy
```

#### Option 4: VPS / Cloud VM (DigitalOcean, AWS, GCP, Azure)

```bash
# On your server
git clone <your-repo>
cd CSP_V2

# Configure environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Deploy with docker-compose
docker-compose --profile production up -d --build

# Set up SSL with Let's Encrypt (certbot)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM/Whisper |
| `BASE_URL` | No | Production URL for PDF generation (e.g., `https://app.example.com`) |
| `SECRET_KEY` | Yes | Flask secret key for sessions (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `PORT` | No | Port to run on (default: 5000 local, 8000 Docker) |
| `REDIS_URL` | No | Redis connection URL (default: `redis://localhost:6379/0`) |
| `FLASK_DEBUG` | No | Enable debug mode - never enable in production! (default: false) |
| `RATE_LIMIT_DEFAULT` | No | Default rate limit (requests per minute, default: 60) |
| `CORS_ORIGINS` | No | CORS origins (comma-separated, default: `*`) |

## Project Structure

```
CSP_V2/
├── app.py                 # Main Flask application
├── ai_generator.py        # Groq LLM integration (prompts, complaint generation)
├── speech.py              # Speech-to-text (Google + Whisper fallback)
├── pdf_generator.py       # PDF generation via Playwright
├── database.py            # SQLite operations
├── requirements.txt       # Python dependencies
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # Local + production orchestration
├── nginx.conf             # Nginx reverse proxy config
├── render.yaml            # Render.com deployment config
├── railway.toml           # Railway deployment config
├── .github/workflows/     # CI/CD pipeline
├── .env.example           # Environment template
├── station_config.json    # Police station configuration
├── templates/             # HTML templates
│   ├── dashboard.html
│   ├── record.html
│   ├── result.html
│   ├── english.html
│   ├── settings.html
│   └── error.html
├── fonts/                 # Telugu font (TiroTelugu-Regular.ttf)
├── audio/                 # Temporary audio uploads
├── case_records/          # Organized case folders (by year/month)
└── generated/             # Temporary PDF generation
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard with statistics & complaint list |
| GET | `/record` | Complaint recording/upload page |
| POST | `/process` | Process audio → generate complaint |
| GET | `/view_telugu/<id>` | View Telugu complaint (HTML) |
| GET | `/view_english/<id>` | View English complaint (HTML) |
| GET | `/case_audio/<path>` | Serve audio files |
| GET | `/settings` | Station configuration page |
| POST | `/save_settings` | Save station config |
| GET | `/health` | Health check endpoint |

## Key Implementation Details

### AI Pipeline

1. **Audio Input** → WebM/WAV/MP3 via browser recording or upload
2. **Speech-to-Text** → Google Speech Recognition (`te-IN`) + Groq Whisper fallback
3. **Text Cleaning** → LLM corrects STT errors, preserves entities
4. **Complaint Generation** → LLM creates formal Telugu FIR (3 paragraphs)
5. **Translation** → LLM translates to natural English preserving all facts
6. **Subject Classification** → LLM generates 5-word Telugu subject
7. **PDF Rendering** → Playwright renders HTML templates to PDF

### Offline-First Design

- Chunked audio upload with resumable support
- IndexedDB caching for offline recording
- Service Worker for asset caching
- Local SQLite database
- Works on unreliable police station networks

### Telugu Language Support

- Noto Sans Telugu / Tiro Telugu fonts bundled
- Unicode PDF generation via Playwright
- Entity preservation (names, dates, IPC sections, vehicle numbers)
- Few-shot prompting with real FIR formats

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest -v
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
black .

# Type checking (optional)
mypy .
```

## Troubleshooting

### Playwright PDF Generation Fails

```bash
# Reinstall browsers
playwright install chromium --with-deps

# In Docker: ensure all dependencies in Dockerfile are present
```

### Audio Conversion Errors

```bash
# Install ffmpeg
# Ubuntu/Debian: apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: choco install ffmpeg
```

### Groq API Rate Limits

- Free tier: 30 RPM, 6000 TPM
- Implement exponential backoff (already in `ai_generator.py`)
- Consider caching for repeated requests

### Database Locked (SQLite)

- Use single worker in production (`gunicorn --workers 1`)
- Or migrate to PostgreSQL for concurrent access

## Scaling Considerations

For production at scale (500+ stations):

1. **Database**: Migrate to PostgreSQL with connection pooling
2. **AI**: Self-host vLLM (Llama-3-8B/70B) for data sovereignty
3. **Queue**: Add Redis + Celery for async PDF generation
4. **Storage**: S3-compatible for audio/PDF files
5. **Auth**: Add JWT/OAuth with RBAC (constable → SI → CI → SP)
6. **Observability**: Prometheus + Grafana + Loki
7. **Edge**: Raspberry Pi 5 / Jetson Orin at each station for offline LLM

## License

MIT License - Feel free to use for community service projects.

## Acknowledgments

- Duvvada Police Station, Gajuwaka, Visakhapatnam for field validation
- Groq for free tier API access
- Playwright team for excellent PDF generation
- Open source contributors

---

**Built as a Community Service Project (CSP) by AI & DS students at Vignan's Institute of Information Technology, Visakhapatnam.**