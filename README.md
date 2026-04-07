# minarai（見習い）

Screen-aware AI companion with pointing & danmaku.  
Local VLM (Qwen3.5-9B). Sees your screen, points at UI elements, teaches and learns.

## What is this?

A macOS menu bar app that:

1. **Points** — Press a hotkey, ask a question. AI sees your screen and points a blue cursor at the exact button/menu you need. All voice, no typing.
2. **Watches** — Continuously captures your screen every 4 seconds. Streams AI commentary as danmaku (bullet comments) flying across your screen.
3. **Learns** — Logs every interaction. Over time, builds workflows from your implicit knowledge. The AI starts as a clueless intern; you teach it by working normally.

Fully local. Zero API costs. Zero cloud dependency.

## Architecture

```
┌─────────────────────────────────────────────┐
│  minarai (Swift, macOS 14+)                 │
│                                             │
│  ┌──────────┐  ┌────────────────────────┐   │
│  │ PTT Mode │  │ Watch Mode             │   │
│  │ (hotkey) │  │ (4s interval capture)  │   │
│  └────┬─────┘  └──────────┬─────────────┘   │
│       │                   │                  │
│       └───────┬───────────┘                  │
│               ▼                              │
│  ┌────────────────────────────────────────┐  │
│  │ vllm-mlx (localhost:8000)             │  │
│  │ Qwen3.5-9B-4bit (~6GB)               │  │
│  │ OpenAI-compatible API                 │  │
│  └──────────────┬────────────────────────┘  │
│                 │                            │
│       ┌─────────┴──────────┐                │
│       ▼                    ▼                 │
│  ┌─────────┐    ┌──────────────────┐        │
│  │ Danmaku │    │ [POINT:x,y:label]│        │
│  │ Overlay │    │ Blue Cursor      │        │
│  └─────────┘    └──────────────────┘        │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ mlx_whisper (STT, ~3GB)            │    │
│  │ Qwen3-TTS (TTS, ~0.4GB)           │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  Total memory: ~9.4GB / 32GB                │
└─────────────────────────────────────────────┘
```

## Requirements

- macOS 14.2+
- Apple Silicon (M1/M2/M3/M4)
- 32GB RAM recommended (16GB minimum with smaller model)
- Xcode 16+

## Setup

```bash
# 1. Start local VLM
pip install "vllm-mlx[vision]"
vllm-mlx serve mlx-community/Qwen3.5-9B-4bit --port 8000

# 2. Build & run
open minarai.xcodeproj
# or
swift build
```

## Inspiration

- [Clicky](https://clicky.so) by Farza — AI buddy with screen pointing (Claude + ElevenLabs)
- [nagare](https://github.com/MAA39/nagare) — Danmaku-based screen awareness (predecessor)
- Gundam's educational computer — Expert data → everyone levels up

## License

MIT
