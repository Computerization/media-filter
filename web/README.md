# Web App (Expo)

Web version of WiseLens (慧眼) built with Expo/React Native.

**Note**: This web app requires the backend service to be running. Unlike the iOS app which calls DeepSeek directly, the web app relies on the Python backend for article crawling and LLM analysis.

## Prerequisites

- Node.js 18+
- npm or yarn
- Backend server running at `http://localhost:8000` (see `../backend/`)

## Quick Start

```bash
# Install dependencies
npm install

# Start web development server
npm run web
```

The app will be available at http://localhost:8081

## Project Structure

```
web/
├── app/                    # File-based routing (expo-router)
│   ├── _layout.tsx         # Root layout with navigation
│   ├── index.tsx           # Home screen (input + analyze)
│   ├── result.tsx          # Analysis result display
│   └── [...rest].tsx       # Catch-all route
├── lib/
│   └── api.ts              # API client configuration
├── assets/                 # Images and static files
├── patches/                # Native patches (for iOS builds)
├── app.json                # Expo configuration
├── package.json            # Dependencies
└── tsconfig.json           # TypeScript config
```

## Development

### Running the Web App

```bash
npm run web
```

Changes to `.tsx` files hot-reload automatically.

### API Configuration

Edit `lib/api.ts` to change the backend URL:

```typescript
const API_BASE_URL = "http://localhost:8000";  // Local development
// const API_BASE_URL = "http://192.168.1.100:8000";  // LAN IP for device testing
```

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run web` | Start web development server |
| `npm start` | Start Expo dev server (all platforms) |
| `npm run ios` | Build and run on iOS simulator |
| `npm run android` | Build and run on Android emulator |

## Key Files

### `app/index.tsx` - Home Screen

Main screen with:
- Instruction card
- Text input for URL/content
- Paste/Clear buttons
- Analyze button with loading state
- Clipboard detection (native only)

### `lib/api.ts` - API Client

```typescript
// Main function to call backend
analyzeContent(url?: string, text?: string): Promise<AnalyzeResponse>

// Helper functions
getVerdictColor(verdict: string): string   // Returns hex color
getVerdictText(verdict: string): string    // Returns Chinese text
```

### `app/result.tsx` - Result Screen

Displays analysis results:
- Verdict with emoji and color
- Summary explanation
- Detailed analysis

## Adding New Features

### Adding a New Screen

1. Create a new file in `app/` directory:
   ```tsx
   // app/settings.tsx
   export default function SettingsScreen() {
     return <View>...</View>;
   }
   ```

2. Navigate to it:
   ```tsx
   import { router } from "expo-router";
   router.push("/settings");
   ```

### Adding a New API Endpoint

1. Add the function in `lib/api.ts`:
   ```typescript
   export async function newEndpoint(params: Params): Promise<Response> {
     const response = await fetch(`${API_BASE_URL}/new-endpoint`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify(params),
     });
     if (!response.ok) throw new Error("Request failed");
     return response.json();
   }
   ```

2. Use it in your component:
   ```tsx
   import { newEndpoint } from "@/lib/api";
   const result = await newEndpoint({ ... });
   ```

## Styling

The app uses React Native's `StyleSheet` API. Colors and styles are defined inline in each component.

Common patterns:
```tsx
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F5",
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
});
```

## Testing

### Manual Testing

1. Start the backend: `cd ../backend && python main.py`
2. Start the web app: `npm run web`
3. Test with a WeChat article URL or plain text

### Test URLs

```
# WeChat article (requires full URL with parameters)
https://mp.weixin.qq.com/s?__biz=...&mid=...&idx=...&sn=...

# Plain text
Any Chinese text content to analyze
```

## Troubleshooting

### "Network request failed"
- Ensure backend is running at the configured `API_BASE_URL`
- Check CORS settings in backend

### Hot reload not working
- Restart the dev server: `npm run web`
- Clear Metro cache: `npx expo start --clear`

### TypeScript errors
- Run `npx tsc --noEmit` to check for type errors
- Ensure `@types/react` is installed

## Notes

- This web version is for browser access only
- For native iOS app with share extension, see the `ios/` directory (local development)
- The share intent feature (`expo-share-intent`) only works on native builds, not web
