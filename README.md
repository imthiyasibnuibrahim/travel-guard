# TravelGuard 🛡️✈️

**Safe Journeys Begin Here**

AI-powered travel safety assistant for first-time travelers from Kerala going to the Gulf (UAE focus).

![TravelGuard Logo](static/logo.png)

## Features

### 🛡️ Offer Check
Verify job offers and detect scam recruitment messages. Supports text and image input (screenshots of WhatsApp messages, emails, etc.).

### 🧳 Pack Check 
Check if your items (medicines, food, electronics) are allowed at your destination. Supports text lists and photos.

### 📋 Journey Checklist
Get a personalised, dated checklist of documents, emigration steps, and layover guidance.

### 🌐 Bilingual
Full English and Malayalam (മലയാളം) support with read-aloud functionality.

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Mobile-first HTML/CSS/JS (single page)
- **AI**: Google Gemini API (text + vision)
- **Data**: Curated JSON files (emigration rules, restricted items)

## Quick Start

### Prerequisites
- Python 3.11+
- Google Gemini API key

### Run Locally

```bash
# Clone and enter the project
cd "Travel Guard"

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key
# Windows:
set GEMINI_API_KEY=your_key_here
# Linux/Mac:
export GEMINI_API_KEY=your_key_here

# Run the app
python main.py
```

Open http://localhost:8000 in your browser.

### Run with Docker

```bash
# Build
docker build -t travelguard .

# Run
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key_here travelguard
```

## Deploy to Render

1. Push code to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `GEMINI_API_KEY` = your key
7. Deploy!

## Deploy to Railway

1. Push code to GitHub
2. Create a new project on [Railway](https://railway.app)
3. Connect your GitHub repo
4. Add environment variable: `GEMINI_API_KEY` = your key
5. Railway auto-detects the Dockerfile and deploys

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main app page |
| GET | `/api/health` | Health check |
| POST | `/api/offer-check` | Analyze job offers for scams |
| POST | `/api/pack-check` | Check items against customs rules |
| POST | `/api/checklist` | Generate travel checklist |

## Demo Mode

Click the **"Demo Mode"** button on the home screen to auto-fill sample data:
- A fake scam job offer (for Offer Check)
- A medicine/item list (for Pack Check)
- Pre-filled trip details (for Checklist)

## Data Files

- `data/emigration_rules.json` - Official emigration rules (MEA, eMigrate, NORKA-Roots)
- `data/restricted_items.json` - UAE customs restricted/prohibited items

## License

MIT
