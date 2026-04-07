#!/usr/bin/env python3
"""
minarai Sprint 0 検証スクリプト

最小構成で「スクショ → VLM → テキスト + [POINT:x,y:label]」を検証する。

使い方:
  # 1. vllm-mlx起動（別ターミナル）
  pip install "vllm-mlx[vision]"
  vllm-mlx serve mlx-community/Qwen3.5-9B-4bit --port 8000

  # 2. スクショを撮って検証
  python3 scripts/verify_pointing.py

  # 3. 既存画像で検証
  python3 scripts/verify_pointing.py --image /path/to/screenshot.png

  # 4. 質問を指定
  python3 scripts/verify_pointing.py --question "カラーグレーディングはどこ？"
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# ── データ構造 ──────────────────────────────────────────

@dataclass
class PointingResult:
    """VLMの指差し結果"""
    spoken_text: str
    point_x: int | None
    point_y: int | None
    point_label: str | None

    @property
    def has_point(self) -> bool:
        return self.point_x is not None

    def __str__(self) -> str:
        if self.has_point:
            return f'"{self.spoken_text}" → [{self.point_x},{self.point_y}:{self.point_label}]'
        return f'"{self.spoken_text}" → [POINT:none]'


# ── [POINT:x,y:label] パーサ ────────────────────────────

POINT_PATTERN = re.compile(r"\[POINT:(\d+),(\d+):(.+?)\]")
POINT_NONE_PATTERN = re.compile(r"\[POINT:none\]")


def parse_pointing_response(raw_response: str) -> PointingResult:
    """VLMレスポンスからテキストと[POINT:x,y:label]を分離する。
    
    Clickyバイナリ解剖から判明した形式:
      "see that menu up top? click that. [POINT:285,11:source control]"
      "html is the skeleton of every web page. [POINT:none]"
    """
    match = POINT_PATTERN.search(raw_response)
    if match:
        spoken_text = POINT_PATTERN.sub("", raw_response).strip()
        return PointingResult(
            spoken_text=spoken_text,
            point_x=int(match.group(1)),
            point_y=int(match.group(2)),
            point_label=match.group(3),
        )

    none_match = POINT_NONE_PATTERN.search(raw_response)
    if none_match:
        spoken_text = POINT_NONE_PATTERN.sub("", raw_response).strip()
        return PointingResult(
            spoken_text=spoken_text,
            point_x=None,
            point_y=None,
            point_label=None,
        )

    # [POINT]タグなし → テキストのみ
    return PointingResult(
        spoken_text=raw_response.strip(),
        point_x=None,
        point_y=None,
        point_label=None,
    )


# ── スクリーンショット取得 ──────────────────────────────

def capture_screenshot(output_path: str = "/tmp/minarai-screenshot.png") -> str:
    """macOSのscreencaptureコマンドでスクショを撮る"""
    print("📸 スクリーンショット取得中...")
    result = subprocess.run(
        ["screencapture", "-x", output_path],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"❌ screencapture失敗: {result.stderr.decode()}")
        sys.exit(1)
    
    file_size = os.path.getsize(output_path)
    if file_size < 1000:
        print("❌ スクショが小さすぎる（画面録画権限がない可能性）")
        print("   システム設定 → プライバシーとセキュリティ → 画面収録 で許可してください")
        sys.exit(1)
    
    print(f"✅ スクショ取得完了: {output_path} ({file_size:,} bytes)")
    return output_path


def encode_image_to_base64(image_path: str) -> str:
    """画像ファイルをbase64エンコード"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── VLM API呼び出し ────────────────────────────────────

# Clickyバイナリ解剖から移植したプロンプト（Qwen3.5用に調整）
SYSTEM_PROMPT = """you are a screen-aware AI assistant.
you can see the user's screen via a screenshot.
your reply will be spoken aloud, so write the way you'd actually talk.

- default to one or two sentences. be direct and dense.
- write for the ear, not the eye. no lists, bullet points, markdown.

you have a pointer that can point at things on screen.
use it whenever pointing would genuinely help the user.
err on the side of pointing rather than not pointing.

when you point, append a coordinate tag at the very end of your response, AFTER your spoken text.
the screenshot image dimensions define the coordinate space.
origin (0,0) is top-left. x increases rightward, y increases downward.

format: [POINT:x,y:label]
where x,y are integer pixel coordinates and label is a 1-3 word element description.

examples:
- "see that source control menu up top? click that and hit commit. [POINT:285,11:source control]"
- "html is the skeleton of every web page. [POINT:none]"
- "that settings gear icon will let you change your preferences. [POINT:1450,680:settings icon]"

if your answer has nothing to do with what's on screen, use [POINT:none]."""


def call_vlm_api(
    base64_image: str,
    user_question: str,
    api_url: str = "http://localhost:8000/v1/chat/completions",
    model: str = "mlx-community/Qwen3.5-9B-4bit",
) -> tuple[str, float]:
    """OpenAI互換APIにスクショ+質問を送信し、テキスト+座標を返す。
    
    screen-commentatorのOllamaService.swiftと同じリクエスト構造。
    vllm-mlxもOpenAI互換なのでそのまま使える。
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    },
                    {
                        "type": "text",
                        "text": user_question,
                    },
                ],
            },
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"\n❌ VLM API接続エラー: {e}")
        print("   vllm-mlxが起動してるか確認してください:")
        print("   vllm-mlx serve mlx-community/Qwen3.5-9B-4bit --port 8000")
        sys.exit(1)
    elapsed = time.time() - t0

    raw_text = data["choices"][0]["message"]["content"]
    return raw_text, elapsed


# ── メモリ計測 ──────────────────────────────────────────

def check_vllm_memory():
    """vllm-mlxプロセスのメモリ使用量を表示"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if "vllm" in line.lower() and "serve" in line.lower():
                parts = line.split()
                rss_kb = int(parts[5]) if len(parts) > 5 else 0
                rss_gb = rss_kb / 1024 / 1024
                print(f"📊 vllm-mlxメモリ使用量: {rss_gb:.1f} GB")
                return rss_gb
    except Exception:
        pass
    return None


# ── メイン ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="minarai Sprint 0: VLM pointing検証")
    parser.add_argument("--image", type=str, help="検証用画像パス（省略時はスクショ撮影）")
    parser.add_argument("--question", type=str, default="この画面で何をしていますか？一番重要なUIエリアを指差してください。",
                        help="VLMに投げる質問")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000/v1/chat/completions",
                        help="VLM APIエンドポイント")
    parser.add_argument("--model", type=str, default="mlx-community/Qwen3.5-9B-4bit",
                        help="使用モデル")
    args = parser.parse_args()

    print("=" * 60)
    print("🔬 minarai Sprint 0: VLM Pointing 検証")
    print("=" * 60)

    # Step 1: 画像取得
    if args.image:
        image_path = args.image
        if not os.path.exists(image_path):
            print(f"❌ 画像が見つかりません: {image_path}")
            sys.exit(1)
        print(f"📎 画像: {image_path}")
    else:
        image_path = capture_screenshot()

    # Step 2: base64エンコード
    base64_image = encode_image_to_base64(image_path)
    print(f"📦 base64サイズ: {len(base64_image):,} chars")

    # Step 3: VLM API呼び出し
    print(f"\n🧠 VLMに質問中: \"{args.question}\"")
    print(f"   API: {args.api_url}")
    print(f"   Model: {args.model}")
    print("   (推論中...)")

    raw_response, elapsed = call_vlm_api(
        base64_image=base64_image,
        user_question=args.question,
        api_url=args.api_url,
        model=args.model,
    )

    # Step 4: [POINT:x,y:label] パース
    result = parse_pointing_response(raw_response)

    # Step 5: 結果表示
    print(f"\n{'=' * 60}")
    print("📋 結果")
    print(f"{'=' * 60}")
    print(f"⏱  推論時間: {elapsed:.1f}秒 {'✅' if elapsed < 10 else '⚠️ 10秒超え'}")
    print(f"💬 テキスト: {result.spoken_text}")
    if result.has_point:
        print(f"👆 指差し: ({result.point_x}, {result.point_y}) → {result.point_label}")
    else:
        print("👆 指差し: なし（[POINT:none]）")
    print(f"\n📝 生レスポンス:\n{raw_response}")

    # Step 6: メモリ確認
    check_vllm_memory()

    # Step 7: 判定
    print(f"\n{'=' * 60}")
    print("🏁 Sprint 0 判定")
    print(f"{'=' * 60}")
    checks = {
        "VLMが意味のあるテキストを返した": len(result.spoken_text) > 10,
        "[POINT:x,y:label]形式で座標を返した": result.has_point,
        "推論時間10秒以内": elapsed < 10,
    }
    all_pass = True
    for check, passed in checks.items():
        print(f"  {'✅' if passed else '❌'} {check}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n🎉 Sprint 0 PASS! → Sprint 1に進んでOK")
    else:
        print("\n⚠️ 一部未達。プロンプト調整 or モデル変更を検討")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
