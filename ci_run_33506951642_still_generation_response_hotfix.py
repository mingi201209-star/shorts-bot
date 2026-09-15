from pathlib import Path


ROOT = Path(__file__).resolve().parent
MARKER = "# RUN_33506951642_STILL_GENERATION_RESPONSE_V2"


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

    decode_anchor = '''    raw = item.get("b64_json")
    if raw:
        return base64.b64decode(raw), prompt
    url = item.get("url")
    if url:
        download = requests.get(url, timeout=120)
        download.raise_for_status()
        return download.content, prompt
    raise RuntimeError("image generation response missing b64_json/url")
'''
    decode_replacement = '''    raw = item.get("b64_json")
    decode_error = None
    if raw:
        try:
            encoded = raw
            if isinstance(encoded, str):
                encoded = encoded.strip()
                if encoded.lower().startswith("data:image/") and "," in encoded:
                    encoded = encoded.split(",", 1)[1]
                encoded = encoded.encode("ascii")
            elif not isinstance(encoded, (bytes, bytearray)):
                raise TypeError(
                    f"image generation b64_json must be str/bytes, got {type(encoded).__name__}"
                )
            decoded = base64.b64decode(encoded)
            if not decoded:
                raise ValueError("decoded image payload is empty")
            return decoded, prompt
        except (ValueError, UnicodeError, binascii.Error, TypeError) as exc:
            decode_error = exc

    url = item.get("url")
    if url:
        if not isinstance(url, str) or not url.strip():
            raise RuntimeError("image generation response url is not a non-empty string")
        download = requests.get(url.strip(), timeout=120)
        download.raise_for_status()
        if not download.content:
            raise RuntimeError("image generation URL returned empty content")
        return download.content, prompt

    if decode_error is not None:
        raise RuntimeError(
            "image generation b64_json decode failed: "
            f"{type(decode_error).__name__}: {decode_error}"
        ) from decode_error
    raise RuntimeError("image generation response missing b64_json/url")
'''
    if text.count(decode_anchor) != 1:
        raise RuntimeError("still response decode anchor mismatch")
    text = text.replace(decode_anchor, decode_replacement, 1)

    failure_anchor = '''    except Exception as exc:
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "
            f"reason={type(exc).__name__}"
        )
        return None
'''
    failure_replacement = '''    except Exception as exc:
        print(
            f"[STILL_IMAGE_FALLBACK] scene={_scene_id(scene)} status=failed "
            f"reason={type(exc).__name__} message={str(exc)[:500]}"
        )
        return None
'''
    if text.count(failure_anchor) != 1:
        raise RuntimeError("still response diagnostic anchor mismatch")
    text = text.replace(failure_anchor, failure_replacement, 1)

    path.write_text(text.rstrip() + f"\n\n{MARKER}\n", encoding="utf-8")
    print("✅ Run 33506951642 still generation response handoff hardened on current main")


if __name__ == "__main__":
    main()
