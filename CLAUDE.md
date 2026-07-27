# CLAUDE.md

WiseLens (慧眼) — helps elderly users spot fake news in WeChat articles. Four independent
surfaces in one repo: `android/`, `ios/`, `web/`, `backend/`.

**Android and iOS call the DeepSeek API directly and do not need `backend/`.** Only `web/` does.

## Commands

### Android (KMP + Jetpack Compose)

```bash
cd android
export ANDROID_HOME=$HOME/Library/Android/sdk   # unset by default; or create local.properties
./gradlew :composeApp:assembleDebug             # -> composeApp/build/outputs/apk/debug/composeApp-debug.apk
./gradlew :composeApp:assembleRelease           # -> .../release/composeApp-release.apk (signed if a keystore is configured)
```

Clean build ~3 min. Or open `android/` in Android Studio and hit Run.

### Backend (only needed by `web/`)

```bash
cd backend && pip install -r requirements.txt && python main.py   # :8000
```
Needs `DEEPSEEK_API_KEY` in `backend/.env`.

### Web (Expo, requires backend running)

```bash
cd web && npm install && npm run web   # :8081
```

### iOS

```bash
cd ios && sh gradlew :composeApp:linkDebugFrameworkIosSimulatorArm64
```
Then open `ios/iosApp/iosApp.xcodeproj` in Xcode. iPhone-only, no iPad.

## Releasing an APK

Push a `v*` tag. `.github/workflows/android-release.yml` builds a signed APK and attaches it
to a GitHub Release:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

`workflow_dispatch` also works for a manual run (takes a version string as input).

`versionName` comes from the tag minus its `v`; `versionCode` is `github.run_number`, so it
always increases — Android requires that for in-place updates. Both flow in as the Gradle
properties `-PappVersionName` / `-PappVersionCode`, defaulting to `1.0` / `1` locally.

Four repo secrets are required — the workflow fails fast with a clear error if
`KEYSTORE_BASE64` is missing, and the `apksigner verify` step blocks publishing an unsigned
APK if any of the others are wrong:

| Secret | Value |
|---|---|
| `KEYSTORE_BASE64` | `base64 -i release.jks` |
| `KEYSTORE_PASSWORD` | keystore password |
| `KEY_ALIAS` | key alias |
| `KEY_PASSWORD` | key password |

**Losing the keystore is unrecoverable** — no future release will install over an existing
install. Back it up outside the repo.

### Signed build locally

Create `android/keystore.properties` (gitignored, as are `*.jks` / `*.keystore`):

```properties
storeFile=/absolute/path/to/release.jks
storePassword=...
keyAlias=...
keyPassword=...
```

Relative `storeFile` paths resolve against `android/`, not `android/composeApp/`.

With no keystore.properties and no `KEYSTORE_*` env vars, `assembleRelease` still succeeds and
emits `composeApp-release-unsigned.apk` — that's the contributor path, don't break it.

Release APKs are signed with v2/v3 only (no `META-INF/*.RSA`); v1 JAR signing isn't needed at
minSdk 24. Use `apksigner verify` to check, not `unzip`.

## BLOCKER: leaked API key

`MediaFilterApi.kt:59` (identical in `android/` and `ios/`) hardcodes a real DeepSeek key:
`private val apiKey = "sk-..."`. It is already public on GitHub — treat it as compromised and
rotate it. Publishing an APK makes it trivially extractable (`unzip` + `strings`), and every
install bills that account. Decide before release: rotate + proxy through `backend/`, ship a
key-less build that prompts the user for their own key, or accept the cost knowingly.

## Architecture

Mobile apps (`android/`, `ios/`) share the same KMP structure, but the two trees are
**independent copies** — `network/MediaFilterApi.kt`, `data/Models.kt`, and `SharedViewModel.kt`
are duplicated, not shared via a common module. A fix in one must be mirrored in the other.

```
android/composeApp/src/
├── commonMain/kotlin/.../     # MediaFilterApi.kt (Ktor + DeepSeek), Models.kt, SharedViewModel.kt
└── androidMain/kotlin/.../    # MainActivity, App.kt, ui/ (Compose), theme/
```

Flow: share a URL from WeChat → `MainActivity` reads `ACTION_SEND` → `MediaFilterApi`
fetches the article HTML and scrapes it **with regex** (`rich_media_title`, `js_content`) →
DeepSeek → verdict `reliable` / `caution` / `misleading`.

The regexes are pinned to WeChat's current HTML. If analysis starts failing on every link,
suspect a WeChat markup change before suspecting the model.

Navigation is a single `currentResult` boolean-ish state in `App.kt`, not a NavHost, despite
`navigation-compose` being on the classpath.

## Gotchas

- **`main.py` ≠ `backend/main.py`.** Root is 1471 lines with Jina-AI-backed web search
  (`search_web`), extra `article_type`/`search_info`/`debug_steps` response fields, and a
  `/test` route. `backend/main.py` is a 341-line subset. README points at `backend/`.
  Confirm which one is canonical before editing either.
- **minSdk 24, but the only launcher icon is `mipmap-anydpi-v26/ic_launcher.xml`** (an
  `<adaptive-icon>`) with no PNG fallback. Cosmetic: the icon won't inflate on API 24–25.
- Release builds have `isMinifyEnabled = false` — no R8, so the APK is ~7.6 MB and all
  strings (including the API key) sit in the clear.
- No tests anywhere in `android/`. The only CI is the release workflow — nothing runs on PRs.
- **`dev.md` is stale** — it predates the Android app and claims the project is only
  backend/ios/web. Prefer this file.
- `android/gradlew` was committed non-executable and has been fixed to `100755`. If
  "permission denied" reappears after a merge, re-run `git update-index --chmod=+x android/gradlew`.

## Identifiers

- Android / Expo: `com.computerization.mediafilter`
- iOS app: `com.wiselens.media-filter` · Share Extension: `...ShareExtension`
- App Group: `group.com.wiselens.computerization` · URL scheme: `mediafilter-kmp`
