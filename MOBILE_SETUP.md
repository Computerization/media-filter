# Mobile App Setup Guide

Follow these steps in order. After completing all steps, let me know and I'll write the code.

## Step 1: Create Expo Project

```bash
cd /Users/wangsicheng/Developer/apps/media_filter
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
```

## Step 2: Install Dependencies

```bash
# Core dependencies
npx expo install expo-router expo-clipboard expo-status-bar react-native-safe-area-context react-native-screens

# Share intent (for receiving shared content)
npm install expo-share-intent --legacy-peer-deps

# Patch package (required for share intent on iOS)
npm install patch-package --save-dev --legacy-peer-deps
```

## Step 3: Create the xcode patch

```bash
mkdir -p patches
```

Then create file `patches/xcode+3.0.1.patch` with this content (I'll provide after you confirm):

Or download it:
```bash
curl -o patches/xcode+3.0.1.patch "https://raw.githubusercontent.com/AChivai/expo-share-intent/main/patches/xcode%2B3.0.1.patch"
```

## Step 4: Update package.json scripts

Add to your package.json scripts section:
```json
"postinstall": "patch-package"
```

## Step 5: Run postinstall

```bash
npm run postinstall
```

## Step 6: Create icon

```bash
mkdir -p assets
# Use any 1024x1024 PNG as assets/icon.png
# Quick option - download a placeholder:
curl -o assets/icon.png "https://via.placeholder.com/1024x1024/4A90D9/ffffff.png"
```

Or create one manually - any 1024x1024 PNG will work.

## Step 7: Confirm setup

Run this to verify everything is installed:
```bash
ls -la node_modules/expo-share-intent
ls -la patches/
ls -la assets/icon.png
```

---

**When you've completed all steps above, reply "done" and I'll write the app code.**
