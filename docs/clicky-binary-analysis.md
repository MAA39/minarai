# Clicky バイナリ解剖レポート

Clickyはクローズドソース。以下はバイナリ（Clicky.app/Contents/MacOS/Clicky）からstringsコマンドで抽出した情報。

## Info.plist

- BundleIdentifier: `com.yourcompany.leanring-buddy`
- LSUIElement: true (Dock非表示、MenuBar常駐)
- MinimumSystemVersion: 14.2
- マイク権限: "Clicky uses your microphone so you can talk to it"
- 画面録画権限: "Clicky needs screen recording access to see your screen and help you."
- 音声認識権限: "Clicky uses speech recognition to transcribe your voice when you talk to it"
- VoiceTranscriptionProvider: assemblyai
- 自動更新: Sparkle (SUFeedURL → julianjear/makesomething-mac-app)
- ビルド環境: Xcode 26.4, macOS SDK 26.4

## ソースファイル一覧（14ファイル）

```
Clicky/CompanionManager.swift          # 中枢。会話状態管理・パイプライン制御
Clicky/CompanionAppDelegate.swift      # アプリ起動・MenuBar常駐
Clicky/ClaudeAPI.swift                 # Anthropic Messages API呼び出し
Clicky/OpenAIAPI.swift                 # OpenAI API（STT用）
Clicky/ElevenLabsTTSClient.swift       # ElevenLabs TTS音声合成
Clicky/CompanionScreenCapture.swift    # ScreenCaptureKit経由のスクショ
Clicky/ElementLocationDetector.swift   # UI要素座標検出（核心）
Clicky/GlobalPushToTalkOverlay.swift   # ホットキー検出・PTTオーバーレイ
Clicky/CompanionResponseOverlay.swift  # 青カーソル（指差し）の描画
Clicky/OverlayWindow.swift            # 透明ウィンドウ管理
Clicky/WindowPositionManager.swift     # カーソル追従位置計算
Clicky/AppleSpeechTranscriptionProvider.swift          # Apple標準STT
Clicky/AssemblyAIStreamingTranscriptionProvider.swift   # AssemblyAI STT
Clicky/OpenAIAudioTranscriptionProvider.swift           # Whisper STT
Clicky/BuddyAudioConversionSupport.swift               # 音声変換
Clicky/GeneratedAssetSymbols.swift     # アセット定数

# アナリティクス
PostHog/PostHogApi.swift
PostHog/PostHogAppLifeCycleIntegration.swift
PostHog/PostHogScreenViewIntegration.swift
PostHog/PostHogErrorTrackingAutoCaptureIntegration.swift
```

## 使用モデル・API

- LLM: `claude-sonnet-4-6`
- TTS: ElevenLabs
- STT優先順位: AssemblyAI → OpenAI Whisper → Apple SFSpeechRecognizer
- API: `https://api.openai.com/v1/audio/transcriptions` (STT用)

## システムプロンプト（メイン会話用）— 全文

```
you're clicky, a friendly always-on companion that lives in the user's menu bar.
the user just spoke to you via push-to-talk and you can see their screen(s).
your reply will be spoken aloud via text-to-speech, so write the way you'd actually talk.
this is an ongoing conversation

- default to one or two sentences. be direct and dense.
  BUT if the user asks you to explain more, go deeper, or elaborate, then go all out
- write for the ear, not the eye. short sentences. no lists, bullet points, markdown, or formatting

you have a small blue triangle cursor that can fly to and point at things on screen.
use it whenever pointing would genuinely help the user

  if they're asking how to do something, looking for a menu, trying to find a button,
  or need help navigating an app, point at the relevant element.
  err on the side of pointing rather than not pointing,
  because it makes your help way more useful and concrete.

  like if the user asks a general knowledge question, or the conversation has nothing
  to do with what's on screen, or you'd just be pointing at something obvious they're
  already looking at. but if there's a specific UI element, menu, button, or area on
  screen that's relevant to what you're helping with, point at it.

when you point, append a coordinate tag at the very end of your response,
AFTER your spoken text.
the screenshot images are labeled with their pixel dimensions.
use those dimensions as the coordinate space.
the origin (0,0) is the top-left corner of the image.
x increases rightward, y increases downward.

format: [POINT:x,y:label]
where x,y are integer pixel coordinates in the screenshot's coordinate space,
and label is a short 1-3 word description of the element
(like "search bar" or "save button").
```

## システムプロンプト（オンボーディング用）

```
you're clicky, a small blue cursor buddy living on the user's screen.
you're showing off during onboarding

  look at their screen and find ONE specific, concrete thing to point at.
  pick something with a clear name or identity:
  a specific app icon (say its name), a specific word or phrase of text you can read,
  a specific filename, a specific button label, a specific tab title,
  a specific image you can describe.
  do NOT point at vague things like "a window" or "some text"

  something fun, playful, or curious that shows you actually read/recognized it.
  no emojis ever. NEVER quote or repeat text you see on screen

CRITICAL COORDINATE RULE:
you MUST only pick elements near the CENTER of the screen.
your x coordinate must be between 20%-80% of the image width.
your y coordinate must be between 20%-80% of the image height.
do NOT pick anything in the top 20%, bottom 20%, left 20%, or right 20% of the screen.
no menu bar items, no dock icons, no sidebar items, no items near any edge.
only things clearly in the middle area of the screen.
if the only interesting things are near the edges,
pick something boring in the center instead.
```

## 指差し出力例（プロンプトから）

```
- "it's right up in the top right area of the toolbar. click that and you'll get all
   the color wheels and curves. [POINT:1100,42:color inspector]"
- "html stands for hypertext markup language, it's basically the skeleton of every
   web page. curious how it connects to the css you're looking at? [POINT:none]"
- "see that source control menu up top? click that and hit commit, or you can use
   command option c as a shortcut. [POINT:285,11:source control]"
```

## 内部変数名（バイナリから抽出）

```
# PTT関連
_isRecordingFromKeyboardShortcut
_isKeyboardShortcutSessionActiveOrFinalizing
_isShortcutCurrentlyPressed
pendingKeyboardShortcutStartTask
BuddyPushToTalkShortcut
GlobalPushToTalkShortcutMonitor
ShortcutTransition

# カーソル関連
cursorTrackingTimer
cursorOffsetX / cursorOffsetY
isCursorScreen
_cursorPosition
_isCursorOnThisScreen
_cursorOpacity
_cursorPositionWhenNavigationStarted
_isReturningToCursor
BlueCursorView / BlueCursorSpinnerView / BlueCursorWaveformView
PointerCursorNSView / PointerCursorView / IBeamCursorNSView

# スクリーンショット
screenshotWidthInPixels / screenshotHeightInPixels
CompanionScreenCapture

# ViewModel
CompanionResponseOverlayViewModel
GlobalPushToTalkOverlayViewModel

# Lazy storage
$__lazy_storage_$_claudeAPI
$__lazy_storage_$_elevenLabsTTSClient
```

## 権限に関するユーザー向けメッセージ（バイナリから）

```
Nothing runs in the background.
Clicky will only take a screenshot when you press the hot key.
So, you can give that permission in peace.
If you are still sus, eh, I can't do much there champ.
```

## STT設定

```
This is a short push-to-talk transcript for a coding and product app.
Expect product names, technical terms, and app-specific vocabulary such as:
```

## Sparkle自動更新

```
SUFeedURL: https://raw.githubusercontent.com/julianjear/makesomething-mac-app/main/appcast.xml
SUPublicEDKey: /l3d2rw5ZZFRU3AadP/w2Zf8FHfhA6bKv16BQOV5OSk=
```
