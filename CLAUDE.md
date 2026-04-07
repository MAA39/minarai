# CLAUDE.md

## プロダクト概要

minarai（見習い）= 画面を見て指差しで教える＋常時認識共有する双方向AI。macOS MenuBarアプリ。

## コアコンセプト

- AIが「できの悪い新入社員」として画面を見て学ぶ（ボトムアップ暗黙知キャプチャ）
- AIが「先輩」として画面上のUI要素を指差して教える（Clicky方式の[POINT:x,y:label]）
- 蓄積されたやり取りからワークフローを自動生成する（BYARD的課題のAI解決）

## 技術スタック

- Swift 6+ / SwiftUI / macOS 14.2+
- vllm-mlx + Qwen3.5-9B-4bit（localhost:8000、OpenAI互換API）
- mlx_whisper（STT）
- ScreenCaptureKit（画面キャプチャ）
- NSWindow透明オーバーレイ（弾幕 + 青カーソル指差し）

## ファイル構成方針

| ファイル名 | 役割 |
|-----------|------|
| MinaraiApp.swift | エントリポイント、MenuBarExtra |
| ScreenCaptureService.swift | SCScreenshotManagerラッパー |
| VisionLanguageModelClient.swift | VLM API呼び出し（localhost:8000） |
| PointingOverlayWindow.swift | 青カーソル描画・座標飛行アニメーション |
| DanmakuOverlayWindow.swift | 弾幕レンダリング |
| PushToTalkManager.swift | GlobalHotKey + マイク録音 |
| SpeechTranscriptionService.swift | mlx_whisper STT |
| ObservationStore.swift | SQLiteログ蓄積 |
| ResponseParser.swift | テキスト + [POINT:x,y:label] パーサ |

## 命名ルール

- 「実装を読みたいと思わせたら負け」— シグネチャだけで挙動が推測できる命名
- 禁止: Manager/Service/Util/Facade（ただし既にServiceが使われている場合は統一性優先）
- 悪い例→良い例: data→screenshot_image / result→vlm_response / run→capture_screen_and_infer

## 指差しプロンプト（Clickyバイナリ解剖から移植）

```
you have a small blue pointer that can fly to and point at things on screen.
use it whenever pointing would genuinely help the user.
err on the side of pointing rather than not pointing.

when you point, append a coordinate tag at the very end of your response:
format: [POINT:x,y:label]
where x,y are integer pixel coordinates in the screenshot's coordinate space.
origin (0,0) is top-left. x increases rightward, y increases downward.
```

## 2モードの優先度制御

- 常時モード: 4秒ごとスクショ→VLM→弾幕（バックグラウンド）
- PTTモード: ホットキー→スクショ→VLM→指差し＋音声回答（フォアグラウンド）
- PTT発火 → 常時モードpause → PTT応答完了 → 常時モードresume

## Linear参照

- プロジェクト: nagare（Linear上は統合管理）
- Clicky解剖ドキュメント: slug f77db236d15d
- Sprint 0: 100-153
- Sprint 0.5（指差し）: 100-241
