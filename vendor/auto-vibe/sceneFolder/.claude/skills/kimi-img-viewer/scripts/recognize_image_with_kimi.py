#!/usr/bin/env python3
"""
Standalone API-style CLI for multimodal image recognition.

It reads a local image, optionally crops/downscales it, wraps it as an
Kimi/OpenAI-compatible image_url content part, and calls /chat/completions.
For Kimi Code's managed plan, pass --use-kimi-code-auth to read and refresh the
local credentials that `kimi login` stores on this machine.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageSequence


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
DEFAULT_PROMPT = "请用中文描述这张图上有什么。"
DEFAULT_TIMEOUT_SECONDS = 300
KIMI_CODE_BASE_URL = "https://api.kimi.com/coding/v1"
KIMI_CODE_MODEL = "k3"
KIMI_CODE_OAUTH_HOST = "https://auth.kimi.com"
KIMI_CODE_CLIENT_ID = "17e5f671-d194-4dfb-9706-5516cb48c098"
KIMI_CODE_OAUTH_PATH = Path.home() / ".kimi-code" / "oauth" / "kimi-code"
KIMI_CODE_CREDENTIALS_PATH = Path.home() / ".kimi-code" / "credentials" / "kimi-code.json"
KIMI_CODE_DEVICE_ID_PATH = Path.home() / ".kimi-code" / "device_id"
KIMI_FULL_RESOLUTION_IMAGE_BUDGET = 3_932_160


@dataclass
class MediaPart:
    kind: str
    source_path: Path
    mime_type: str
    data: bytes
    original_width: int | None
    original_height: int | None
    sent_width: int | None
    sent_height: int | None
    note: str


@dataclass
class KimiCodeAuth:
    access_token: str
    refreshed: bool


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_region(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    pieces = [piece.strip() for piece in value.split(",")]
    if len(pieces) != 4:
        fail("--region must be x,y,width,height")
    try:
        x, y, width, height = [int(piece) for piece in pieces]
    except ValueError:
        fail("--region values must be integers")
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        fail("--region requires x>=0, y>=0, width>0, height>0")
    return x, y, width, height


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image/jpeg" if suffix in {".jpg", ".jpeg"} else f"image/{suffix[1:]}"
    return "application/octet-stream"


def fit_within_edge(image: Image.Image, max_edge: int) -> Image.Image:
    if max_edge <= 0:
        return image
    width, height = image.size
    edge = max(width, height)
    if edge <= max_edge:
        return image
    copy = image.copy()
    copy.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return copy


def encode_image(image: Image.Image, prefer_png: bool, quality: int) -> tuple[bytes, str]:
    has_alpha = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if prefer_png or has_alpha:
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if has_alpha else "RGB")
        with tempfile.SpooledTemporaryFile() as tmp:
            image.save(tmp, format="PNG", optimize=True)
            tmp.seek(0)
            return tmp.read(), "image/png"

    if image.mode != "RGB":
        image = image.convert("RGB")
    with tempfile.SpooledTemporaryFile() as tmp:
        image.save(tmp, format="JPEG", quality=quality, optimize=True)
        tmp.seek(0)
        return tmp.read(), "image/jpeg"


def prepare_image(
    path: Path,
    *,
    region: tuple[int, int, int, int] | None,
    full_resolution: bool,
    max_edge: int,
    max_bytes: int,
) -> MediaPart:
    try:
        image = Image.open(path)
        image.load()
    except Exception as exc:  # noqa: BLE001
        fail(f"cannot open image {path}: {exc}")

    if getattr(image, "is_animated", False):
        image = next(ImageSequence.Iterator(image)).copy()

    original_width, original_height = image.size
    note_parts: list[str] = []

    if region is not None:
        x, y, width, height = region
        if x + width > original_width or y + height > original_height:
            fail(
                f"--region exceeds image bounds: image is "
                f"{original_width}x{original_height}"
            )
        image = image.crop((x, y, x + width, y + height))
        note_parts.append(f"cropped region {x},{y},{width},{height}")

    if not full_resolution:
        before = image.size
        image = fit_within_edge(image, max_edge)
        if image.size != before:
            note_parts.append(f"downscaled {before[0]}x{before[1]} -> {image.size[0]}x{image.size[1]}")

    prefer_png = path.suffix.lower() == ".png"
    quality = 90
    data, mime_type = encode_image(image, prefer_png=prefer_png, quality=quality)

    if full_resolution and len(data) > KIMI_FULL_RESOLUTION_IMAGE_BUDGET:
        fail(
            f"{path} is {len(data)} bytes, over Kimi Code's "
            f"{KIMI_FULL_RESOLUTION_IMAGE_BUDGET}-byte per-image "
            "full_resolution limit; use --region or omit --full-resolution"
        )

    if not full_resolution:
        while len(data) > max_bytes and max(image.size) > 512:
            next_edge = max(512, int(max(image.size) * 0.75))
            image = fit_within_edge(image, next_edge)
            quality = max(70, quality - 5)
            data, mime_type = encode_image(image, prefer_png=False, quality=quality)
        if len(data) > max_bytes:
            fail(
                f"encoded image is {len(data)} bytes, over --max-bytes={max_bytes}; "
                "try --region or a smaller --max-edge"
            )

    return MediaPart(
        kind="image",
        source_path=path,
        mime_type=mime_type,
        data=data,
        original_width=original_width,
        original_height=original_height,
        sent_width=image.size[0],
        sent_height=image.size[1],
        note="; ".join(note_parts) if note_parts else "full image",
    )


def kimi_version() -> str:
    configured = os.getenv("KIMI_CODE_VERSION")
    if configured:
        return configured
    try:
        result = subprocess.run(
            [str(Path.home() / ".kimi-code" / "bin" / "kimi"), "--version"],
            text=True,
            capture_output=True,
            timeout=2,
            check=False,
        )
        version = result.stdout.strip() or result.stderr.strip()
        if version:
            return version.splitlines()[0].strip()
    except Exception:  # noqa: BLE001
        pass
    return "0.23.3"


def device_model() -> str:
    system = platform.system()
    machine = platform.machine()
    if system == "Darwin":
        try:
            version = subprocess.run(
                ["/usr/bin/sw_vers", "-productVersion"],
                text=True,
                capture_output=True,
                timeout=1,
                check=False,
            ).stdout.strip()
        except Exception:  # noqa: BLE001
            version = platform.release()
        return f"macOS {version or platform.release()} {machine}".strip()
    return f"{system} {platform.release()} {machine}".strip()


def ascii_header(value: str, fallback: str = "unknown") -> str:
    cleaned = "".join(ch for ch in value if 32 <= ord(ch) <= 126).strip()
    return cleaned or fallback


def kimi_code_user_agent() -> str:
    version = ascii_header(kimi_version(), fallback="0.23.3")
    if version.startswith("kimi-code-cli/"):
        return version
    return f"kimi-code-cli/{version}"


def kimi_device_headers() -> dict[str, str]:
    try:
        device_id = KIMI_CODE_DEVICE_ID_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        device_id = ""
    return {
        "User-Agent": kimi_code_user_agent(),
        "X-Msh-Platform": "kimi_code_cli",
        "X-Msh-Version": ascii_header(kimi_version()),
        "X-Msh-Device-Name": ascii_header(socket.gethostname()),
        "X-Msh-Device-Model": ascii_header(device_model()),
        "X-Msh-Os-Version": ascii_header(platform.release()),
        "X-Msh-Device-Id": ascii_header(device_id),
    }


def data_url(part: MediaPart) -> str:
    encoded = base64.b64encode(part.data).decode("ascii")
    return f"data:{part.mime_type};base64,{encoded}"


def read_token_file(path: Path, *, allow_empty: bool = False) -> str:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail(f"cannot read Kimi Code OAuth token file {path}: {exc}")
    if not raw:
        if allow_empty:
            return ""
        fail(f"Kimi Code OAuth token file is empty: {path}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    candidates: list[Any] = [
        data.get("access_token") if isinstance(data, dict) else None,
        data.get("accessToken") if isinstance(data, dict) else None,
        data.get("token") if isinstance(data, dict) else None,
    ]
    if isinstance(data, dict) and isinstance(data.get("tokens"), dict):
        tokens = data["tokens"]
        candidates.extend([tokens.get("access_token"), tokens.get("accessToken")])
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    fail(f"could not find access_token in {path}")


def refresh_kimi_code_credentials(path: Path, data: dict[str, Any]) -> KimiCodeAuth:
    refresh_token = data.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        fail(f"{path} has no refresh_token; run `kimi login` again")

    oauth_host = os.getenv("KIMI_CODE_OAUTH_HOST") or os.getenv("KIMI_OAUTH_HOST") or KIMI_CODE_OAUTH_HOST
    url = f"{oauth_host.rstrip('/')}/api/oauth/token"
    try:
        response = requests.post(
            url,
            headers={
                **kimi_device_headers(),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": KIMI_CODE_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        fail(f"failed to refresh Kimi Code token: {exc}")

    try:
        payload = response.json()
    except json.JSONDecodeError:
        fail(f"Kimi OAuth refresh returned non-JSON HTTP {response.status_code}: {response.text[:1000]}")

    if response.status_code != 200:
        detail = payload.get("error_description") or payload.get("message") or payload.get("error") or payload
        fail(f"Kimi OAuth refresh failed HTTP {response.status_code}: {detail}")

    access_token = payload.get("access_token")
    new_refresh_token = payload.get("refresh_token") or refresh_token
    expires_in = int(payload.get("expires_in") or 0)
    if not isinstance(access_token, str) or not access_token:
        fail("Kimi OAuth refresh response missing access_token")
    if expires_in <= 0:
        fail("Kimi OAuth refresh response missing valid expires_in")

    next_data = {
        **data,
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "expires_at": int(time.time()) + expires_in,
        "scope": payload.get("scope", data.get("scope", "")),
        "token_type": payload.get("token_type", data.get("token_type", "Bearer")),
        "expires_in": expires_in,
    }
    path.write_text(json.dumps(next_data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return KimiCodeAuth(access_token=access_token, refreshed=True)


def read_kimi_credentials(path: Path, *, force_refresh: bool = False) -> KimiCodeAuth:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        fail(f"cannot read Kimi Code credentials {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Kimi Code credentials are not valid JSON: {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"Kimi Code credentials file is not a JSON object: {path}")

    access_token = data.get("access_token")
    expires_at = int(data.get("expires_at") or 0)
    should_refresh = force_refresh or not isinstance(access_token, str) or not access_token or expires_at <= int(time.time()) + 300
    if should_refresh:
        return refresh_kimi_code_credentials(path, data)
    return KimiCodeAuth(access_token=access_token, refreshed=False)


def read_kimi_code_access_token(credentials_path: Path) -> KimiCodeAuth:
    return read_kimi_credentials(credentials_path)


def resolve_api_settings(args: argparse.Namespace) -> tuple[str, str, str]:
    explicit_env = os.getenv(args.api_key_env) if args.api_key_env else None
    key_from_env = (
        explicit_env
        or os.getenv("KIMI_CODE_ACCESS_TOKEN")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("KIMI_API_KEY")
        or os.getenv("MOONSHOT_API_KEY")
    )
    api_key = args.api_key or key_from_env
    if args.use_kimi_code_auth and not api_key:
        api_key = read_kimi_code_access_token(Path(args.kimi_credentials_path).expanduser()).access_token
    if not api_key and not args.dry_run and not args.metadata_only:
        fail(
            "missing API key. Set KIMI_CODE_ACCESS_TOKEN, KIMI_API_KEY, "
            "MOONSHOT_API_KEY, or OPENAI_API_KEY; or pass --use-kimi-code-auth"
        )

    if args.base_url:
        base_url = args.base_url
    elif args.use_kimi_code_auth or os.getenv("KIMI_CODE_ACCESS_TOKEN"):
        base_url = KIMI_CODE_BASE_URL
    elif os.getenv("OPENAI_BASE_URL"):
        base_url = os.environ["OPENAI_BASE_URL"]
    elif os.getenv("KIMI_BASE_URL"):
        base_url = os.environ["KIMI_BASE_URL"]
    elif os.getenv("MOONSHOT_BASE_URL"):
        base_url = os.environ["MOONSHOT_BASE_URL"]
    elif os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY"):
        base_url = "https://api.moonshot.cn/v1"
    else:
        base_url = KIMI_CODE_BASE_URL

    model = (
        args.model
        or os.getenv("VISION_MODEL")
        or os.getenv("KIMI_CODE_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("KIMI_MODEL")
        or KIMI_CODE_MODEL
    )

    return api_key or "", base_url.rstrip("/"), model


def build_payload(args: argparse.Namespace, model: str, parts: list[MediaPart]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": args.prompt}]
    for part in parts:
        image_url: dict[str, Any] = {"url": data_url(part)}
        if args.detail:
            image_url["detail"] = args.detail
        content.append({"type": "image_url", "image_url": image_url})

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": args.temperature,
    }
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens
    return payload


def call_chat_completions(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: int,
) -> str:
    url = f"{base_url}/chat/completions"
    response = requests.post(
        url,
        headers={
            "User-Agent": kimi_code_user_agent(),
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        fail(f"HTTP {response.status_code} from {url}: {response.text[:2000]}")

    try:
        body = response.json()
    except json.JSONDecodeError:
        fail(f"non-JSON response: {response.text[:2000]}")

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(json.dumps(body, ensure_ascii=False, indent=2))
        fail("response did not match OpenAI-compatible chat/completions shape")


def metadata(parts: list[MediaPart], base_url: str, model: str) -> dict[str, Any]:
    return {
        "endpoint": f"{base_url}/chat/completions",
        "model": model,
        "media": [
            {
                "kind": part.kind,
                "path": str(part.source_path),
                "mime_type": part.mime_type,
                "bytes": len(part.data),
                "original_dimensions": (
                    [part.original_width, part.original_height]
                    if part.original_width is not None and part.original_height is not None
                    else None
                ),
                "sent_dimensions": (
                    [part.sent_width, part.sent_height]
                    if part.sent_width is not None and part.sent_height is not None
                    else None
                ),
                "note": part.note,
            }
            for part in parts
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read a local image and call a Kimi/OpenAI-compatible vision model."
    )
    parser.add_argument("path", help="image path")
    parser.add_argument(
        "-p",
        "--prompt",
        "-q",
        "--question",
        dest="prompt",
        default=DEFAULT_PROMPT,
        help=f"question for the vision model (default: {DEFAULT_PROMPT})",
    )
    parser.add_argument(
        "--model",
        help=f"vision model name (default: {KIMI_CODE_MODEL}); env: KIMI_CODE_MODEL/VISION_MODEL",
    )
    parser.add_argument(
        "--base-url",
        help=f"API base URL (default: {KIMI_CODE_BASE_URL})",
    )
    parser.add_argument("--api-key", help="API key. Prefer env vars instead of this option.")
    parser.add_argument("--api-key-env", help="read API key from this env var first")
    parser.add_argument(
        "--use-kimi-code-auth",
        action="store_true",
        help="read and refresh ~/.kimi-code/credentials/kimi-code.json written by `kimi login`",
    )
    parser.add_argument(
        "--kimi-credentials-path",
        default=str(KIMI_CODE_CREDENTIALS_PATH),
        help=f"Kimi Code credentials path (default: {KIMI_CODE_CREDENTIALS_PATH})",
    )
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument("--detail", choices=["low", "high", "auto"], default="auto")
    parser.add_argument("--region", help="image crop: x,y,width,height in original pixels")
    parser.add_argument("--full-resolution", action="store_true", help="skip downscaling")
    parser.add_argument("--max-edge", type=int, default=2000, help="max image edge before sending")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=4 * 1024 * 1024,
        help="max encoded image bytes before base64",
    )
    parser.add_argument("--metadata-only", action="store_true", help="print image metadata and exit")
    parser.add_argument("--dry-run", action="store_true", help="print request metadata, do not call API")
    parser.add_argument("--kimi-bin", help=argparse.SUPPRESS)
    parser.add_argument("--raw", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not any(
        [
            args.api_key,
            args.api_key_env,
            os.getenv("KIMI_CODE_ACCESS_TOKEN"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("KIMI_API_KEY"),
            os.getenv("MOONSHOT_API_KEY"),
        ]
    ):
        args.use_kimi_code_auth = True
    path = Path(args.path).expanduser()
    if not path.exists():
        fail(f"file not found: {path}")
    if not path.is_file():
        fail(f"path is not a file: {path}")

    mime_type = guess_mime(path)
    region = parse_region(args.region)
    if not (mime_type.startswith("image/") or path.suffix.lower() in IMAGE_SUFFIXES):
        fail(f"unsupported image type: {mime_type}")

    parts = [
        prepare_image(
            path,
            region=region,
            full_resolution=args.full_resolution,
            max_edge=args.max_edge,
            max_bytes=args.max_bytes,
        )
    ]

    api_key, base_url, model = resolve_api_settings(args)
    meta = metadata(parts, base_url, model)
    if args.metadata_only or args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    payload = build_payload(args, model, parts)
    print(call_chat_completions(api_key=api_key, base_url=base_url, payload=payload, timeout=args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
