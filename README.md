# WiseLens (慧眼)

A mobile application designed to help the elderly identify fake news and misleading information online.

## Project Structure

```
media_filter/
├── backend/          # Python FastAPI Backend (for web app)
│   ├── main.py       # API Service
│   ├── requirements.txt
│   └── .env.example
├── ios/              # iOS App - iPhone only (Kotlin Multiplatform + SwiftUI)
│   ├── composeApp/   # Shared Kotlin logic (calls DeepSeek API directly)
│   └── iosApp/       # SwiftUI app + Share Extension
├── android/          # Android App (Kotlin Multiplatform + Jetpack Compose)
│   ├── composeApp/   # Shared Kotlin logic + Compose UI
│   └── gradle/       # Gradle build configuration
└── web/              # Web App (Expo) - requires backend
    ├── app/          # Application Pages (Router)
    └── lib/          # Utilities & API client
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

### 2. Run iOS App (iPhone only, no backend required)

```bash
cd ios
./gradlew :composeApp:linkDebugFrameworkIosSimulatorArm64
```

Then open `ios/iosApp/iosApp.xcodeproj` in Xcode and run.

**Note**: The iOS app calls DeepSeek API directly and does not require the backend service.

### 3. Run Android App (no backend required)

1. Open the `android/` folder in **Android Studio**
2. Wait for Gradle sync to complete
3. Select an emulator or connect a physical device (API 24+)
4. Click **Run ▶** to build and launch

**Note**: The Android app calls DeepSeek API directly, same as the iOS version.

### 4. Run Web App (requires backend)

```bash
cd web
npm install
npm run web
```

The web app will run at http://localhost:8081

**Note**: The web app requires the backend service to be running.

## Features

- [x] WeChat Official Account article link analysis
- [x] Direct text input analysis
- [x] Credibility assessment (Reliable / Caution / Misleading)
- [x] Detailed analysis explanations
- [x] iOS Share Extension (share directly from Safari/WeChat)
- [x] Android Share Intent (share from WeChat/browsers)
- [x] Dark/Light theme support
- [ ] Douyin video analysis (Planned)
- [ ] WeChat Video Channel analysis (Planned)

## Tech Stack

- **Backend**: Python, FastAPI, BeautifulSoup, DeepSeek API
- **iOS**: Kotlin Multiplatform, SwiftUI, Ktor
- **Android**: Kotlin Multiplatform, Jetpack Compose, Ktor
- **Web**: React Native (Expo), TypeScript

## Computerization

Developed by the **Computerization** club, **with the assistance of deep neural networks** (to learn more, see [AI Lab](https://github.com/WFLA-AI-Lab)). We are dedicated to helping the community through technology.
