from pathlib import Path


def append_once(text, marker, block):
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + block.strip() + "\n"


# Run 34616204901 was mechanically GREEN but failed human review on three axes:
# weak/repetitive opening copy, context-only aircraft stock, and three consecutive
# tiny/repetitive AIRCRAFT_WINDOW_STRESS_V1 panels.  This hotfix is intentionally
# a quality-floor patch only: no API/still/retry/cost/threshold budget changes.

# 1) Script: make opening information progression a hard structural property.
script_path = Path("content/script_generator.py")
script_text = script_path.read_text(encoding="utf-8")
_prompt_anchor = "[CAUSAL NARRATIVE + NEW INFORMATION — REQUIRED]\n"
_prompt_block = (
    "[HUMAN QUALITY OPENING — REQUIRED]\n"
    "첫 두 Scene에서 같은 관찰 사실을 말만 바꿔 반복하지 않는다. 특히 Scene 1의 관찰을 Scene 2에서 '왜/이유는 무엇일까요' 형태로 다시 묻지 않는다.\n"
    "Scene 1은 구체적으로 보이는 사실을 짧게 제시하고, Scene 2는 그 사실에 없던 새 단서·제약·작동 방향 중 하나를 추가한다.\n"
    "근거보다 강한 공포·속도·인과 표현을 보태지 말고 trusted claim의 강도에 맞춰 담백하게 설명한다.\n"
)
if "[HUMAN QUALITY OPENING — REQUIRED]" not in script_text and _prompt_anchor in script_text:
    script_text = script_text.replace(_prompt_anchor, _prompt_anchor + _prompt_block, 1)

script_text = append_once(
    script_text,
    "RUN_34616204901_HUMAN_SCRIPT_FLOOR_V1",
    r'''
# RUN_34616204901_HUMAN_SCRIPT_FLOOR_V1
_HQ_OPENING_STOPWORDS = {
    "그런데", "그리고", "하지만", "그래서", "되어", "됩니다", "있습니다",
    "무엇일까요", "왜일까요", "이유", "이유는", "정도", "정말", "바로",
}
_HQ_KOREAN_PARTICLES = (
    "으로부터", "에서부터", "에게서", "까지는", "이라는", "라는", "으로", "에서",
    "에게", "처럼", "보다", "부터", "까지", "이나", "거나", "하고", "이며",
    "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "와", "과",
)


def _hq_opening_terms(text):
    raw = re.findall(r"[0-9A-Za-z가-힣]+", str(text or "").lower())
    terms = set()
    for token in raw:
        if len(token) < 2 or token in _HQ_OPENING_STOPWORDS:
            continue
        compact = token
        for suffix in _HQ_KOREAN_PARTICLES:
            if compact.endswith(suffix) and len(compact) - len(suffix) >= 2:
                compact = compact[:-len(suffix)]
                break
        if len(compact) >= 2 and compact not in _HQ_OPENING_STOPWORDS:
            terms.add(compact)
    return terms


def _hq_opening_repeat_issue(scenes):
    if not isinstance(scenes, list) or len(scenes) < 2:
        return None
    first = str((scenes[0] or {}).get("text", "")).strip() if isinstance(scenes[0], dict) else ""
    second = str((scenes[1] or {}).get("text", "")).strip() if isinstance(scenes[1], dict) else ""
    if not first or not second:
        return None
    first_terms = _hq_opening_terms(first)
    second_terms = _hq_opening_terms(second)
    if not first_terms or not second_terms:
        return None
    shared = first_terms & second_terms
    overlap = len(shared) / max(1, min(len(first_terms), len(second_terms)))
    second_reasks_reason = bool(re.search(r"(?:왜|이유|무엇일까요|어째서)", second))
    if second_reasks_reason and len(shared) >= 2 and overlap >= 0.50:
        return (
            "scene 2 re-asks scene 1 instead of adding a new information unit "
            f"(shared={','.join(sorted(shared))})"
        )
    return None


_hq_previous_validate_script = validate_script


def validate_script(result):
    valid, reason = _hq_previous_validate_script(result)
    if not valid:
        return valid, reason
    if not isinstance(result, dict):
        return valid, reason
    issue = _hq_opening_repeat_issue(result.get("scenes", []))
    if issue:
        return False, f"Human Quality Opening 실패: {issue}"
    return True, reason
''',
)
script_path.write_text(script_text, encoding="utf-8")


# 2) Stock: for an aircraft+window anchored scene, UNKNOWN evidence is not
# enough.  We do not promote metadata to visual proof; verified reuse remains
# legal.  This closes the Run 34616204901 clouds/wing contextual-stock escape.
video_path = Path("video/video_downloader.py")
video_text = video_path.read_text(encoding="utf-8")
video_text = append_once(
    video_text,
    "RUN_34616204901_WINDOW_VISIBLE_PROOF_V1",
    r'''
# RUN_34616204901_WINDOW_VISIBLE_PROOF_V1
_hq_previous_general_scene_unknown_safe_tier = general_scene_unknown_safe_tier


def _hq_aircraft_window_anchor_query(scene_query):
    anchors = set(extract_query_anchors(scene_query))
    return "aircraft" in anchors and "window" in anchors


def general_scene_unknown_safe_tier(candidate, scene_query):
    tier, label = _hq_previous_general_scene_unknown_safe_tier(candidate, scene_query)
    if not _hq_aircraft_window_anchor_query(scene_query):
        return tier, label
    visual = candidate_visible_component_evidence(candidate, scene_query)
    state = str(visual.get("state") or "UNKNOWN").upper()
    if state == "UNKNOWN" and tier >= 3:
        return 5, "WINDOW_SUBJECT_REQUIRES_VISIBLE_PROOF"
    return tier, label
''',
)
video_path.write_text(video_text, encoding="utf-8")


# 3) Deterministic explanation: keep the existing grounded template/contract,
# but turn the three owned claims into visibly different, mobile-sized beats.
# LEFT/RIGHT meaning stays fixed; only emphasis/viewpoint/animation changes.
visual_path = Path("video/visual_explanation.py")
visual_text = visual_path.read_text(encoding="utf-8")
visual_text = append_once(
    visual_text,
    "RUN_34616204901_GUIDED_COMPARISON_V1",
    r'''
# RUN_34616204901_GUIDED_COMPARISON_V1
_hq_previous_plan_explanation = plan_explanation
_hq_previous_draw_concept_panel = _draw_concept_panel

_HQ_WINDOW_PRESENTATIONS = {
    "squarish_window_stress_concentration": {
        "scene_role": "constraint",
        "action": "stress_concentration",
        "label": "각진 모서리에 응력이 집중됩니다",
        "active": "LEFT",
    },
    "rounded_window_stress_distribution": {
        "scene_role": "mechanism_change",
        "action": "stress_distribution",
        "label": "둥근 모서리는 응력을 분산시킵니다",
        "active": "RIGHT",
    },
    "squarish_window_fatigue_rupture": {
        "scene_role": "primary_result",
        "action": "fatigue_crack_risk",
        "label": "응력 집중은 피로 균열을 키웁니다",
        "active": "LEFT",
    },
}


def _hq_window_profile_for_claim(claim_id):
    return dict(_HQ_WINDOW_PRESENTATIONS.get(str(claim_id or ""), {}))


def plan_explanation(scene):
    plan = _hq_previous_plan_explanation(scene)
    if not plan or plan.get("template") != "AIRCRAFT_WINDOW_STRESS_V1":
        return plan
    claim_id = str(plan.get("owned_claim_id") or "")
    profile = _hq_window_profile_for_claim(claim_id)
    if not profile:
        return plan
    plan = dict(plan)
    plan.update({
        "scene_role": profile["scene_role"],
        "action": profile["action"],
        "label": profile["label"],
        "motion_profile": "GUIDED_COMPARISON",
        "presentation_signature": f"AIRCRAFT_WINDOW_STRESS_V1:{claim_id}",
        "active_side": profile["active"],
    })
    print(
        "[HUMAN_QUALITY_PRESENTATION] "
        f"template=AIRCRAFT_WINDOW_STRESS_V1 claim={claim_id} "
        f"profile=GUIDED_COMPARISON active={profile['active']}"
    )
    return plan


def _hq_panel_box(draw, box, *, active):
    fill = (22, 28, 38, 225) if active else (12, 16, 24, 150)
    outline = (255, 255, 255, 220) if active else (255, 255, 255, 80)
    width = 5 if active else 2
    draw.rounded_rectangle(box, radius=34, fill=fill, outline=outline, width=width)


def _hq_draw_sharp_window(draw, box, *, active, progress, fatigue=False):
    x1, y1, x2, y2 = box
    alpha = 250 if active else 95
    line = (235, 238, 244, alpha)
    corner_x = x1 + 92
    corner_y = y2 - 150
    draw.line((corner_x, y1 + 75, corner_x, corner_y), fill=line, width=26)
    draw.line((corner_x, corner_y, x2 - 65, corner_y), fill=line, width=26)
    if active:
        pulse = 58 + int(24 * math.sin(max(0.0, min(1.0, progress)) * math.pi))
        for deg in (190, 215, 240, 265, 290, 315, 340):
            angle = math.radians(deg)
            ex = corner_x + pulse * math.cos(angle)
            ey = corner_y + pulse * math.sin(angle)
            draw.line((corner_x, corner_y, ex, ey), fill=(245, 78, 78, 245), width=10)
        if fatigue:
            drift = int(9 * math.sin(max(0.0, min(1.0, progress)) * math.pi))
            crack = [
                (corner_x + 3, corner_y - 4),
                (corner_x + 34, corner_y - 42 - drift),
                (corner_x + 19, corner_y - 78 - drift),
                (corner_x + 55, corner_y - 112 - drift),
                (corner_x + 42, corner_y - 150 - drift),
            ]
            draw.line(crack, fill=(255, 198, 95, 255), width=8)


def _hq_draw_rounded_window(draw, box, *, active, progress):
    x1, y1, x2, y2 = box
    alpha = 250 if active else 95
    inset = 58
    window = (x1 + inset, y1 + 78, x2 - inset, y2 - 135)
    draw.rounded_rectangle(window, radius=105, outline=(235, 238, 244, alpha), width=26)
    if active:
        wx1, wy1, wx2, wy2 = window
        cx = wx1 + 105
        cy = wy2 - 105
        shift = 8.0 * math.sin(max(0.0, min(1.0, progress)) * math.pi)
        for r_off in (-28, -8, 12, 32):
            rr = 105 + r_off
            points = []
            for deg in range(90, 181, 6):
                angle = math.radians(deg + shift)
                points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
            draw.line(points, fill=(105, 195, 255, 245), width=9)


def _draw_concept_panel(frame, plan, progress):
    if (plan or {}).get("template") != "AIRCRAFT_WINDOW_STRESS_V1":
        return _hq_previous_draw_concept_panel(frame, plan, progress)

    claim_id = str((plan or {}).get("owned_claim_id") or "")
    profile = _hq_window_profile_for_claim(claim_id)
    if not profile:
        return _hq_previous_draw_concept_panel(frame, plan, progress)

    draw = ImageDraw.Draw(frame, "RGBA")
    panel = (36, 76, VIDEO_WIDTH - 36, 1390)
    draw.rounded_rectangle(
        panel, radius=42, fill=(3, 8, 17, 232),
        outline=(255, 255, 255, 185), width=3,
    )
    title = _font(52)
    side_font = _font(38)
    caption = _font(42)
    small = _font(31)

    draw.text((72, 112), profile["label"], font=title, fill=(255, 255, 255, 252))
    draw.text((72, 184), "같은 압력에서도 모서리 모양이 응력 흐름을 바꿉니다", font=small, fill=(190, 205, 225, 235))

    left = (68, 260, 520, 1165)
    right = (560, 260, 1012, 1165)
    left_active = profile["active"] == "LEFT"
    right_active = profile["active"] == "RIGHT"
    _hq_panel_box(draw, left, active=left_active)
    _hq_panel_box(draw, right, active=right_active)

    draw.text((105, 292), "각진 창문", font=side_font, fill=(255, 255, 255, 245 if left_active else 135))
    draw.text((602, 292), "둥근 창문", font=side_font, fill=(255, 255, 255, 245 if right_active else 135))

    _hq_draw_sharp_window(
        draw, left, active=left_active, progress=progress,
        fatigue=(claim_id == "squarish_window_fatigue_rupture"),
    )
    _hq_draw_rounded_window(draw, right, active=right_active, progress=progress)

    if claim_id == "squarish_window_stress_concentration":
        draw.text((104, 1030), "응력이 한곳에 몰림", font=caption, fill=(255, 130, 130, 255))
        draw.text((613, 1030), "비교 대상", font=caption, fill=(190, 195, 205, 145))
    elif claim_id == "rounded_window_stress_distribution":
        draw.text((120, 1030), "비교 대상", font=caption, fill=(190, 195, 205, 145))
        draw.text((600, 1030), "곡선을 따라 분산", font=caption, fill=(145, 215, 255, 255))
    else:
        draw.text((92, 1010), "반복 응력 → 피로 균열", font=caption, fill=(255, 201, 115, 255))
        draw.text((615, 1030), "둥근 모서리", font=caption, fill=(190, 195, 205, 145))

    draw.text((72, 1242), "LEFT  각진 모서리", font=small, fill=(225, 230, 238, 225))
    draw.text((577, 1242), "RIGHT  둥근 모서리", font=small, fill=(225, 230, 238, 225))
    return frame
''',
)
visual_path.write_text(visual_text, encoding="utf-8")

print("✅ Run 34616204901 human-quality floor installed: script progression, visible window proof, guided comparison")
