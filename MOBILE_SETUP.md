# Mobile App Setup Guide

This guide explains how to set up the mobile application with native share capabilities.

## Step 1: Initialize Project (Reference only)

```bash
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
```

## Step 2: Install Dependencies

```bash
# Core dependencies
npx expo install expo-router expo-clipboard expo-status-bar react-native-safe-area-context react-native-screens

# Share intent (for receiving shared content from other apps)
npm install expo-share-intent --legacy-peer-deps

# Patch package (required for share intent fix on iOS)
npm install patch-package --save-dev --legacy-peer-deps
```

## Step 3: Configure iOS Share Extension

The project uses `expo-share-intent` to allow users to share WeChat articles directly to the app.

1. **Patch Xcode**: Ensure the patch is applied.
   ```bash
   npm run postinstall
   ```

2. **iOS Build**: When running `npx expo run:ios`, the native share extension target will be automatically configured by the `expo-share-intent` plugin.

## Step 4: Run the App

### Development Server
```bash
npm start
```

### Local Native Build (Simulator)
```bash
npx expo run:ios
```

## Development Workflow

1. **Changing JS/TS code**: Changes will hot-reload automatically via Metro.
2. **Changing Native Config**: If you modify `app.json` plugins or native files, you must run `npx expo run:ios` again to rebuild the binary.

---

**Developed by Computerization**