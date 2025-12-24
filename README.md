# Media Filter (信息鉴别助手)

A mobile application designed to help the elderly identify fake news and misleading information online.

## Project Structure

```
media_filter/
├── backend/          # Python FastAPI Backend
│   ├── main.py       # API Service
│   ├── requirements.txt
│   └── .env.example
└── mobile/           # Expo React Native Mobile App
    ├── app/          # Application Pages (Router)
    ├── lib/          # Utilities & API client
    └── package.json
```

## Quick Start

### 1. Start Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API Key
cp .env.example .env
# Edit .env and fill in your DEEPSEEK_API_KEY
# Note: Currently uses DeepSeek API (OpenAI compatible)

# Start service
python main.py
```

The backend will run at http://localhost:8000

### 2. Start Mobile App

```bash
cd mobile

# Install dependencies
npm install

# Start development server
npm start
```

Scan the QR code with the **Expo Go** app to preview.

**Note**: If testing on a physical device, update `API_BASE_URL` in `mobile/lib/api.ts` to your computer's local IP address.

## Features

- [x] WeChat Official Account article link analysis
- [x] Direct text input analysis
- [x] Credibility assessment (Reliable / Caution / Misleading)
- [x] Detailed analysis explanations
- [ ] Douyin video analysis (Planned)
- [ ] WeChat Video Channel analysis (Planned)

## Tech Stack

- **Backend**: Python, FastAPI, BeautifulSoup, DeepSeek API
- **Mobile**: React Native, Expo, TypeScript

## Computerization

Developed by the **Computerization** club, with the assistance of deep neural networks (to learn more, see [AI Lab](https://github.com/WFLA-AI-Lab)). We are dedicated to helping the community through technology.