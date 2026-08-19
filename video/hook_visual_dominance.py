import base64
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import openai

from config import OPENAI_KEY
from quality.budget_guard import authorize_call, print_budget_status, record_usage


openai.api_key = OPENAI_KEY

HOOK_DOMINANCE_MODEL = os.environ.get("HOOK_DOMINANCE_MODEL", "gpt-4o-mini")
HOOK_SUBJECT_DOMINANCE_MIN = 8.0
HOOK_ACTION_MATCH_MIN = 7.0
HOOK_MAX_COMPETING_SUBJECT_RISK = 4.0
HOOK_EARLY_FRAME_TIMES = (0.0, 0.5, 1.5, 2.5)

_OBSERVABLE_ACTION_TERMS = {
    "회전", "회전하", "돌아", "도는", "돌고", "움직", "흐르", "날아",
    "뛰", "달리", "걷", "열리", "닫히", "타오르", "떨어", "흔들",
    "구르", "분사", "솟", "감기", "펼치", "접히", "파도치", "하품",
    "rotating", "rotate", "spinning", "spin", "turning", "moving",
    "running", "flowing", "flying", "walking", "driving", "opening",
    "closing", "burning", "falling", "rolling", "swirling", "waving",
    "yawning", "yawn",
}


def requires_observable_action(scene):
    combined = " ".join(
        str(scene.get(key, "") or "")
        for key in ("text", "keyword", "visual_goal")
    ).lower()
    words = set(re.findall(r"[a-z]+", combined))
    if words & _OBSERVABLE_ACTION_TERMS:
        return True
    return any(term in combined for term in _OBSERVABLE_ACTION_TERMS if not term.isascii())


def normalize_dominance_result(payload, *, action_required):
    if not isinstance(payload, dict):
        raise ValueError("Hook dominance result must be a JSON object")

    def score(name, default=0.0):
        try:
            value = float(payload.get(name, default))
        except Exception:
            value = default
        return round(max(0.0, min(value, 10.0)), 3)

    return {
        "target_subject": str(payload.get("target_subject", "")).strip(),
        "subject_dominance": score("subject_dominance"),
        "action_match": score("action_match", 10.0 if not action_required else 0.0),
        "competing_subject_risk": score("competing_subject_risk"),
        "vertical_crop_subject_visible": bool(payload.get("vertical_crop_subject_visible", False)),
        "target_is_person": bool(payload.get("target_is_person", False)),
        "action_required": bool(action_required),
        "reason": str(payload.get("reason", "")).strip()[:500],
    }


def passes_dominance_gate(result):
    if not result.get("vertical_crop_subject_visible"):
        return False
    if float(result.get("subject_dominance", 0.0)) < HOOK_SUBJECT_DOMINANCE_MIN:
        return False
    if float(result.get("competing_subject_risk", 10.0)) > HOOK_MAX_COMPETING_SUBJECT_RISK:
        return False
    if result.get("action_required") and float(result.get("action_match", 0.0)) < HOOK_ACTION_MATCH_MIN:
        return False
    return True


def _extract_json(text):
    text = str(text or "").strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError("Hook dominance response did not contain JSON")


def _extract_vertical_frames(video_url):
    with tempfile.TemporaryDirectory(prefix="hook_dominance_") as temp_dir:
        temp = Path(temp_dir)
        pattern = temp / "frame_%02d.jpg"
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,fps=2"
        )
        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_url),
            "-t", "2.7",
            "-vf", vf,
            "-q:v", "3",
            str(pattern),
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=75,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Hook dominance frame extraction failed: {result.stderr[-600:]}")

        generated = sorted(temp.glob("frame_*.jpg"))
        if len(generated) < 2:
            raise RuntimeError("Hook dominance frame extraction produced too few frames")

        # fps=2 yields frames around 0.0, 0.5, 1.0, 1.5, 2.0, 2.5.
        wanted = (0, 1, 3, 5)
        selected = [generated[index] for index in wanted if index < len(generated)]
        encoded = []
        for path in selected:
            encoded.append(base64.b64encode(path.read_bytes()).decode("ascii"))
        return encoded


def evaluate_hook_subject_dominance(candidate, scene):
    action_required = requires_observable_action(scene)
    frames = _extract_vertical_frames(candidate.get("url"))

    hook_text = str(scene.get("text", "") or "").strip()
    visual_goal = str(scene.get("visual_goal", "") or "").strip()
    keyword = str(scene.get("keyword", "") or "").strip()

    prompt = f"""
You are a strict first-3-seconds mobile Shorts visual inspector.
The supplied images are EARLY FRAMES AFTER the exact production center-crop to 1080x1920.
Evaluate only what is visibly present in these frames.

Hook narration: {hook_text}
Visual goal: {visual_goal}
Search keyword: {keyword}
Observable action required: {str(action_required).lower()}

Identify the concrete subject explicitly promised by the Hook. Then score:
- subject_dominance (0-10): the Hook subject itself must be large, central/salient, visually dominant over other subjects, and identifiable on a phone within about 0.5 seconds.
- action_match (0-10): if the Hook promises an observable action, the action itself must be visibly evident across the early frames. Mere subject presence is not enough.
- competing_subject_risk (0-10): another face/person/vehicle/text/animal/object visually dominates or strongly competes with the Hook subject. Do NOT count a person as competing when the Hook subject itself is a person.
- vertical_crop_subject_visible: false if the 9:16 crop makes the promised subject small, cut off, peripheral, or hard to identify.

Examples:
- Hook about a rotating snake: snake close-up with clear movement = high dominance/action and low competing risk.
- Hook about a rotating snake: large human holding a small snake = low dominance, high competing risk even though a snake exists.
- Hook about a rotating snake: large static snake = high dominance but low action_match.
- Hook about a yawning person: a human face close-up can be valid because the person is the promised subject, but the promised yawn still needs visible action match.

Return JSON only:
{{
  "target_subject": "short label",
  "target_is_person": false,
  "subject_dominance": 0,
  "action_match": 0,
  "competing_subject_risk": 0,
  "vertical_crop_subject_visible": false,
  "reason": "short concrete explanation"
}}
"""

    content = [{"type": "text", "text": prompt}]
    for encoded in frames:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encoded}",
                "detail": "low",
            },
        })

    call_number = authorize_call(HOOK_DOMINANCE_MODEL)
    print(f"💳 Hook dominance vision call authorized: #{call_number}")
    response = openai.chat.completions.create(
        model=HOOK_DOMINANCE_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Judge first-frame subject dominance and visible action conservatively. "
                    "Do not infer unseen content from metadata."
                ),
            },
            {"role": "user", "content": content},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    usage = record_usage(HOOK_DOMINANCE_MODEL, response)
    print(f"💰 Hook dominance vision call: ${usage['cost_usd']:.6f}")
    print_budget_status()

    payload = _extract_json(response.choices[0].message.content)
    result = normalize_dominance_result(payload, action_required=action_required)
    result["frame_times"] = list(HOOK_EARLY_FRAME_TIMES)
    result["pass"] = passes_dominance_gate(result)
    return result
