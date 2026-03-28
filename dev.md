## Project Overview

WiseLens (慧眼) is a mobile application designed to help elderly users identify fake news and misleading information, primarily in WeChat articles. It consists of:

- **backend/** - Python FastAPI service that crawls articles and uses DeepSeek LLM for analysis (used by web app)
- **ios/** - Primary iOS app (iPhone-only) built with Kotlin Multiplatform + SwiftUI. Calls DeepSeek API directly without backend.
- **web/** - Expo-based web app that connects to the backend service

## Build & Run Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py                    # Runs on http://localhost:8000
```
Requires `DEEPSEEK_API_KEY` in `.env` file.

### iOS App (Kotlin Multiplatform)
```bash
cd ios
./gradlew :composeApp:linkDebugFrameworkIosSimulatorArm64   # Build for simulator
./gradlew :composeApp:linkDebugFrameworkIosArm64            # Build for device
```
Then open `ios/iosApp/iosApp.xcodeproj` in Xcode and run.

### Web App (Expo)
```bash
cd web
npm install
npm run web                       # Web version at localhost:8081
```

## Architecture

### Data Flow

**iOS App (standalone - no backend required):**
1. User shares URL from WeChat/Safari via Share Extension, or pastes content
2. App fetches and parses WeChat article HTML directly (Ktor + regex)
3. Sends content to DeepSeek API for credibility analysis
4. Returns verdict: `reliable` (✅), `caution` (⚠️), or `misleading` (❌)

**Web App (requires backend):**
1. User pastes URL or text content
2. Web app sends POST to backend `/analyze` endpoint
3. Backend crawls WeChat article (BeautifulSoup) and calls DeepSeek LLM
4. Returns verdict to web app

### Key Files

**Backend:**
- `main.py` - FastAPI routes, WeChat crawler, and LLM integration

**iOS (KMP):**
- `composeApp/src/commonMain/kotlin/.../network/MediaFilterApi.kt` - Ktor HTTP client (update `baseUrl` for device testing)
- `composeApp/src/commonMain/kotlin/.../data/Models.kt` - Shared data models
- `iosApp/iosApp/ContentView.swift` - SwiftUI main view with dark/light theme
- `iosApp/ShareExtension/ShareViewController.swift` - iOS share extension
- `iosApp/ShareExtension/ShareExtensionPreprocessor.js` - Extracts original URL from WeChat pages

**Web (Expo):**
- `app/index.tsx` - Home screen
- `lib/api.ts` - API client

### iOS Share Extension

The iOS app uses a native Swift share extension with App Group `group.com.wiselens.computerization`. WeChat modifies URLs via `history.replaceState`, stripping parameters. The share extension uses a JavaScript preprocessor to extract the original URL from meta tags (og:url, canonical).

## Network Configuration

For physical device testing, update API URLs from `localhost` to your Mac's LAN IP:
- iOS: `ios/composeApp/src/commonMain/kotlin/.../network/MediaFilterApi.kt` → `baseUrl`
- Web: `web/lib/api.ts` → `API_BASE_URL`

## Bundle Identifiers

- iOS App: `com.wiselens.media-filter` (iPhone-only, no iPad support)
- iOS Share Extension: `com.wiselens.media-filter.ShareExtension`
- App Group: `group.com.wiselens.computerization`
- URL Scheme: `mediafilter-kmp`
- Web/Expo: `com.computerization.mediafilter`
