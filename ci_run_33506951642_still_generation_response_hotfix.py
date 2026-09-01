from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# RUN_33506951642_STILL_GENERATION_RESPONSE_V1"


def main():
    path = ROOT / "video/still_image_fallback.py"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    import_anchor = "import base64\nimport hashlib\n"
    import_replacement = "import base64\nimport binascii\nimport hashlib\n"
    if text.count(import_anchor) != 1:
        raise RuntimeError("still response import anchor mismatch")
    text = text.replace(import_anchor, import_replacement, 1)

    decode_anchor = '''    raw = item.get("b64_json")\n    if raw:\n        return base64.b64decode(raw), prompt\n    url = item.get("url")\n    if url:\n        download = requests.get(url, timeout=120)\n        download.raise_for_status()\n        return download.content, prompt\n    raise RuntimeError("image generation response missing b64_json/url")\n'''
    decode_replacement = '''    raw = item.get("b64_json")\n    decode_error = None\n    if raw:\n        try:\n            encoded = raw\n            if isinstance(encoded, str):\n                encoded = encoded.strip()\n                # Accept a standards-compliant data URI without changing the\n                # physical image identity or requesting another generation.\n                if encoded.lower().startswith("data:image/") and "," in encoded:\n                    encoded = encoded.split(",", 1)[1]\n                encoded = encoded.encode("ascii")\n            elif not isinstance(encoded, (bytes, bytearray)):\n                raise TypeError(\n                    f"image generation b64_json must be str/bytes, got {type(encoded).__name__}"\n                )\n            decoded = base64.b64decode(encoded)\n            if not decoded:\n                raise ValueError("decoded image payload is empty")\n            return decoded, prompt\n        except (ValueError, UnicodeError, binascii.Error, TypeError) as exc:\n            decode_error = exc\n\n    url = item.get("url")\n    if url:\n        if not isinstance(url, str) or not url.strip():\n            raise RuntimeError("image generation response url is not a non-empty string")\n        download = requests.get(url.strip(), timeout=120)\n        download.raise_for_status()\n        if not download.content:\n            raise RuntimeError("image generation URL returned empty content")\n        return download.content, prompt\n\n    if decode_error is not None:\n        raise RuntimeError(\n            "image generation b64_json decode failed: "\n            f"{type(decode_error).__name__}: {decode_error}"\n        ) from decode_error\n    raise RuntimeError("image generation response missing b64_json/url")\n'''
    if text.count(decode_anchor) != 1:
        raise RuntimeError("still response decode anchor mismatch")
    text = text.replace(decode_anchor, decode_replacement, 1)

    failure_anchor = '''    except Exception as exc:\n        print(\n            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "\n            f"reason={type(exc).__name__}"\n        )\n        return None\n'''
    failure_replacement = '''    except Exception as exc:\n        print(\n            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "\n            f"reason={type(exc).__name__} message={str(exc)[:500]}"\n        )\n        return None\n'''
    if text.count(failure_anchor) != 1:
        raise RuntimeError("still response diagnostic anchor mismatch")
    text = text.replace(failure_anchor, failure_replacement, 1)

    path.write_text(text.rstrip() + f"\n\n{MARKER}\n", encoding="utf-8")
    print("✅ Run 33506951642 still generation response handoff hardened")


if __name__ == "__main__":
    main()
