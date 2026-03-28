# WiseLens iOS App

Native iOS app (iPhone-only) built with Kotlin Multiplatform for shared logic and SwiftUI for the UI.

## Prerequisites

- **macOS** with Xcode 15+
- **JDK 17+** (for Gradle/Kotlin compilation)
- **CocoaPods** (optional, not currently used)

## Project Structure

```
ios/
├── composeApp/                    # Kotlin Multiplatform shared code
│   ├── build.gradle.kts
│   └── src/commonMain/kotlin/
│       ├── data/Models.kt         # Data models (AnalyzeResponse, etc.)
│       ├── network/MediaFilterApi.kt  # DeepSeek API client + WeChat crawler
│       └── SharedViewModel.kt     # ViewModel for iOS integration
├── iosApp/                        # Native iOS app
│   ├── iosApp/
│   │   ├── iosAppApp.swift        # App entry point + URL scheme handling
│   │   ├── ContentView.swift      # Main SwiftUI views
│   │   ├── iosApp.entitlements    # App Group configuration
│   │   └── Info.plist
│   ├── ShareExtension/            # iOS Share Extension
│   │   ├── ShareViewController.swift
│   │   ├── ShareExtensionPreprocessor.js
│   │   └── ShareExtension.entitlements
│   └── iosApp.xcodeproj
└── gradle/                        # Gradle wrapper
```

## Building

### 1. Build Kotlin Framework

```bash
cd ios

# For iPhone Simulator (Apple Silicon Mac)
./gradlew :composeApp:linkDebugFrameworkIosSimulatorArm64

# For physical iPhone device
./gradlew :composeApp:linkDebugFrameworkIosArm64
```

### 2. Open in Xcode

```bash
open iosApp/iosApp.xcodeproj
```

Select your target device/simulator and click Run.

## Architecture

### Kotlin Multiplatform Layer (`composeApp/`)

- **MediaFilterApi.kt**: Handles all network operations
  - Fetches and parses WeChat article HTML directly
  - Calls DeepSeek API for content analysis
  - Supports streaming responses for chat feature
  - No backend server required

- **Models.kt**: Shared data structures
  - `AnalyzeResponse`: Analysis result with verdict, summary, details
  - `ChatMessage`: For follow-up Q&A

- **SharedViewModel.kt**: Bridge between Kotlin and Swift
  - Exposes `analyzeContent()` and `streamChat()` to SwiftUI

### SwiftUI Layer (`iosApp/`)

- **ContentView.swift**: Main UI
  - Home screen with URL/text input
  - Result view with analysis display
  - Chat interface for follow-up questions
  - Dark/light theme support

- **Share Extension**: Allows sharing directly from Safari/WeChat
  - Uses JavaScript preprocessor to extract original URLs
  - Communicates with main app via App Group

## Configuration

### Bundle Identifiers

| Component | Identifier |
|-----------|------------|
| Main App | `com.wiselens.media-filter` |
| Share Extension | `com.wiselens.media-filter.ShareExtension` |
| App Group | `group.com.wiselens.computerization` |
| URL Scheme | `mediafilter-kmp` |

### API Key

The DeepSeek API key is embedded in `MediaFilterApi.kt`. For production, consider:
- Using a backend proxy
- Environment-based configuration
- iOS Keychain storage

## Features

- Direct WeChat article URL analysis
- Plain text content analysis
- Share Extension for quick sharing from other apps
- Follow-up Q&A with AI assistant
- Streaming responses
- Dark/light theme
- iPhone-optimized UI

## Troubleshooting

### Framework not found

Make sure you've built the correct framework for your target:
- Simulator: `linkDebugFrameworkIosSimulatorArm64`
- Device: `linkDebugFrameworkIosArm64`

### Share Extension not working

Verify App Group IDs match in:
- `iosApp.entitlements`
- `ShareExtension.entitlements`
- `iosAppApp.swift` (appGroupIdentifier)
- `ShareViewController.swift` (appGroupIdentifier)

All should be: `group.com.wiselens.computerization`
