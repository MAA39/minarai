# Clicky OSS ソースコード解析（2026/04/08更新）

2026/04/08 OSSとして公開: https://github.com/farzaa/clicky

## ファイル構成（7751行、22 Swiftファイル）

| ファイル | 行数 | 役割 | minarai流用度 |
|---------|------|------|-------------|
| CompanionManager.swift | 1026 | 中枢。PTT→スクショ→Claude→TTS→指差しの全パイプライン | ★★★ 構造をそのまま真似 |
| OverlayWindow.swift | 881 | 青カーソル+ベジェ曲線飛行アニメーション+マルチモニタ | ★★★ 飛行アニメーションを流用 |
| DesignSystem.swift | 880 | UI定数・色・角丸 | ★ 参考程度 |
| BuddyDictationManager.swift | 866 | PTT録音パイプライン（AVAudioEngine+STT連携） | ★★★ PTT実装を流用 |
| CompanionPanelView.swift | 761 | MenuBar UIパネル | ★★ UI参考 |
| AssemblyAIStreamingTranscriptionProvider.swift | 478 | AssemblyAI WebSocket STT | ☆ minaraiではmlx_whisper |
| ElementLocationDetector.swift | 335 | Computer Use API座標検出（精密版） | ☆ ローカルVLMでは使えない |
| OpenAIAudioTranscriptionProvider.swift | 317 | OpenAI Whisper STT | ☆ minaraiではmlx_whisper |
| ClaudeAPI.swift | 291 | Claude API+SSEストリーミング | ★★ OpenAI互換APIに差替 |
| WindowPositionManager.swift | 262 | ウィンドウ配置+権限フロー | ★★ 権限チェック流用 |
| MenuBarPanelManager.swift | 243 | NSStatusItem+NSPanel管理 | ★★★ MenuBar実装そのまま |
| CompanionResponseOverlay.swift | 217 | 応答テキスト吹き出し+ウェーブフォーム | ★★ UI流用 |
| AppleSpeechTranscriptionProvider.swift | 147 | Apple Speech STT | ★ フォールバック用 |
| OpenAIAPI.swift | 142 | OpenAI GPT API | ☆ 不使用 |
| GlobalPushToTalkShortcutMonitor.swift | 132 | CGEventTapグローバルホットキー | ★★★ そのまま流用 |
| CompanionScreenCaptureUtility.swift | 132 | SCScreenshotManager+マルチモニタ | ★★★ そのまま流用 |
| ClickyAnalytics.swift | 121 | PostHog | ☆ 不使用 |
| BuddyAudioConversionSupport.swift | 108 | PCM16変換+WAV構築 | ★★ 音声処理流用 |
| BuddyTranscriptionProvider.swift | 100 | STTプロバイダ抽象層 | ★ 参考 |
| leanring_buddyApp.swift | 89 | アプリエントリポイント | ★★★ 構造を真似 |
| ElevenLabsTTSClient.swift | 81 | ElevenLabs TTS | ☆ minaraiではsay/Qwen3-TTS |
| worker/src/index.ts | 142 | CFプロキシ | ☆ 不使用 |

## 核心パイプライン（CompanionManager.swift:586-700）

```
PTTホットキー押下 (GlobalPushToTalkShortcutMonitor)
  ↓ .pressed
BuddyDictationManager.startPushToTalk()
  ↓ AVAudioEngine → PCM16 → AssemblyAI WebSocket
PTTホットキー離す
  ↓ .released → transcript確定
sendTranscriptToClaudeWithScreenshot(transcript)
  ↓
CompanionScreenCaptureUtility.captureAllScreensAsJPEG()
  ↓ 全ディスプレイ→JPEG→ラベル付き（"screen 1 of 2 — cursor is on this screen"）
  ↓ 各画像に "(image dimensions: 1280x831 pixels)" を付与
ClaudeAPI.analyzeImageStreaming(images, systemPrompt, conversationHistory, userPrompt)
  ↓ SSEストリーミング → fullResponseText
parsePointingCoordinates(from: fullResponseText)
  ↓ [POINT:x,y:label:screenN] をパース
  ↓ スクショpx座標 → ディスプレイpoint座標 → AppKitグローバル座標
detectedElementScreenLocation = globalLocation
  ↓ BlueCursorView が onChange で検知
animateBezierFlightArc(to: destination)
  ↓ 60fps Timer → ベジェ曲線飛行（0.6-1.4秒）
startPointingAtElement()
  ↓ 吹き出し表示 "right here!" → 3秒保持
startFlyingBackToCursor()
  ↓ カーソル位置に帰還
finishNavigationAndResumeFollowing()
```

## 指差し座標変換（CompanionManager.swift:648-674）

```
Claude応答: [POINT:850,42:color inspector]
  ↓ スクショ空間 (1280x831px)
clamp(0, min(850, 1280)) → 850
clamp(0, min(42, 831)) → 42
  ↓ ディスプレイpoint空間 (1512x982pt) に変換
displayLocalX = 850 * (1512/1280) = 1004
displayLocalY = 42 * (982/831) = 49.6
  ↓ AppKit座標系（bottom-left origin）に変換
appKitY = 982 - 49.6 = 932.4
  ↓ グローバル座標
globalX = 1004 + displayFrame.origin.x
globalY = 932.4 + displayFrame.origin.y
```

## ベジェ曲線飛行アニメーション（OverlayWindow.swift:491-567）

```
quadratic bezier: B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
- P0 = 現在位置（カーソル追従位置）
- P1 = 制御点（中間点から上に arcHeight だけオフセット）
- P2 = 目標座標
- arcHeight = min(distance * 0.2, 80px)
- 飛行時間 = clamp(distance/800, 0.6s, 1.4s)
- easing: smoothstep (3t²-2t³)
- 回転: ベジェ接線の方向に三角形が向く
- スケール: sin(t*π) で中間点で1.3x拡大
```

## システムプロンプト全文（CompanionManager.swift:544-577）

（全文は docs/clicky-binary-analysis.md に記載済み。OSS公開により完全一致を確認）

## スクショ設定（CompanionScreenCaptureUtility.swift:83-97）

```swift
let maxDimension = 1280  // 最大幅1280px
configuration.width = maxDimension
configuration.height = Int(CGFloat(maxDimension) / aspectRatio)
// → JPEG quality 0.8
// → 自アプリのウィンドウは除外（ownAppWindows）
```

## minaraiとの差分マッピング

| Clicky | minarai差替 | 理由 |
|--------|-----------|------|
| ClaudeAPI.swift → api.anthropic.com | VLMClient → localhost:8000 (vllm-mlx) | ローカル完結 |
| ElevenLabsTTSClient.swift → ElevenLabs API | macOS `say` → Qwen3-TTS MLX | コストゼロ |
| AssemblyAI WebSocket STT | mlx_whisper (Python sidecar) | ローカル完結 |
| Cloudflare Worker (worker/) | 削除 | 不要 |
| ElementLocationDetector.swift | 削除 | Computer Use API不使用 |
| PostHog Analytics | 削除 | 不要 |
| SSEストリーミング | 非ストリーミング（vllm-mlxは通常レスポンス） | ローカルは十分速い |
| **追加: 常時弾幕モード** | DanmakuOverlayWindow | Clickyにない機能 |
| **追加: SQLite蓄積** | ObservationStore | 暗黙知→形式知 |

## minaraiが「そのまま流用」すべきファイル TOP5

1. **GlobalPushToTalkShortcutMonitor.swift** (132行) — CGEventTap。変更不要
2. **CompanionScreenCaptureUtility.swift** (132行) — SCScreenshotManager。変更不要
3. **OverlayWindow.swift** (881行) — 青カーソル+ベジェ飛行。TTS/onboarding部分を削除
4. **leanring_buddyApp.swift** (89行) — エントリポイント。リネーム
5. **MenuBarPanelManager.swift** (243行) — NSStatusItem+NSPanel。UIカスタマイズ

## minaraiが「参考にして書き直す」ファイル

1. **CompanionManager.swift** — ClaudeAPI→VLMClient差替、常時弾幕モード追加
2. **ClaudeAPI.swift** — OpenAI互換API（localhost:8000）に書き換え
3. **BuddyDictationManager.swift** — AssemblyAI→mlx_whisperに差替
4. **CompanionPanelView.swift** — UI差し替え

## minaraiが「不要」なファイル

- ElementLocationDetector.swift（Computer Use API）
- AssemblyAIStreamingTranscriptionProvider.swift
- OpenAIAudioTranscriptionProvider.swift
- OpenAIAPI.swift
- ClickyAnalytics.swift
- ElevenLabsTTSClient.swift（将来Qwen3-TTS）
- worker/（全体）
