"""Offline regression: V2 renderer must consume the exact accepted asset."""

import os
import tempfile
from pathlib import Path

from quality_core_v2.schemas import CandidateVisualV2, SceneV2, VisualPlanV2
from quality_core_v2.selected_scene_renderer import create_scene_from_selected_visual


class _FakeAudio:
    def __init__(self, _path):
        self.duration = 4.0
    def close(self):
        pass


class _FakeVideo:
    duration = 4.0
    def close(self):
        pass


class _FakeComposite:
    def __init__(self, _layers, size=None):
        self.size = size
        self.duration = 0.0
    def set_audio(self, _audio):
        return self
    def set_duration(self, duration):
        self.duration = duration
        return self
    def close(self):
        pass


def test_exact_selected_media_url_is_downloaded_without_research():
    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "flex",
        "new_information": "flex visible",
        "visual_requirement": "aircraft main wing visible upward bending",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward bending"],
        "search_queries": ["aircraft wing flex"],
    })
    visual = CandidateVisualV2.from_dict({
        "source_type": "stock",
        "description": "aircraft main wing visible upward bending",
        "visible_components": ["aircraft", "main wing"],
        "observable_state": ["visible upward bending"],
        "provider": "pexels",
        "source_id": "accepted-42",
        "media_url": "https://cdn.example/exact-accepted-42.mp4",
    })

    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            downloaded = []

            def paths(_idx):
                return {
                    "audio": "scene.mp3",
                    "source_video": "source.mp4",
                    "vertical_video": "vertical.mp4",
                }

            def voice(_text, path):
                Path(path).write_bytes(b"audio")

            def download(url, path):
                downloaded.append(url)
                Path(path).write_bytes(b"video")

            def prepare(_source, output, _duration):
                Path(output).write_bytes(b"vertical")

            clip = create_scene_from_selected_visual(
                0,
                scene,
                plan,
                visual,
                create_voice_fn=voice,
                get_scene_paths_fn=paths,
                download_video_fn=download,
                prepare_vertical_video_fn=prepare,
                load_video_for_scene_fn=lambda *_: _FakeVideo(),
                create_subtitle_clips_fn=lambda *_args, **_kwargs: [],
                audio_clip_cls=_FakeAudio,
                composite_clip_cls=_FakeComposite,
                verify_rendered_visual_fn=lambda *_args: type(
                    "V", (), {"passed": True, "reason": "ok"}
                )(),
            )
            assert downloaded == ["https://cdn.example/exact-accepted-42.mp4"]
            assert clip.duration == 4.0
        finally:
            os.chdir(old)


def test_renderer_source_contains_no_provider_search_call():
    source = Path(__file__).with_name("selected_scene_renderer.py").read_text(
        encoding="utf-8"
    )
    assert "fetch_pexels_video" not in source
    assert "search_pexels_candidates" not in source
    assert "search_pixabay_candidates" not in source


if __name__ == "__main__":
    test_exact_selected_media_url_is_downloaded_without_research()
    test_renderer_source_contains_no_provider_search_call()
    test_rendered_visual_qa_failure_blocks_scene_before_composition()
    print("V2 EXACT-ASSET RENDER REGRESSION: PASS (3/3)")


def test_rendered_visual_qa_failure_blocks_scene_before_composition():
    scene = SceneV2.from_dict({
        "scene_index": 1,
        "narration": "aircraft wing flex visible",
        "causal_role": "phenomenon",
        "owned_claim_id": "flex",
        "new_information": "flex visible",
        "visual_requirement": "aircraft main wing visible upward bending",
    })
    plan = VisualPlanV2.from_dict({
        "scene_index": 1,
        "subject": "aircraft main wing",
        "required_visible_components": ["aircraft", "main wing"],
        "required_observable_state": ["visible upward bending"],
        "search_queries": ["aircraft wing flex"],
    })
    visual = CandidateVisualV2.from_dict({
        "source_type": "stock",
        "description": "aircraft main wing",
        "visible_components": ["aircraft", "main wing"],
        "observable_state": ["visible upward bending"],
        "provider": "pexels",
        "source_id": "accepted-43",
        "media_url": "https://cdn.example/exact-accepted-43.mp4",
    })

    with tempfile.TemporaryDirectory() as tmp:
        old = os.getcwd()
        os.chdir(tmp)
        try:
            def paths(_idx):
                return {
                    "audio": "scene.mp3",
                    "source_video": "source.mp4",
                    "vertical_video": "vertical.mp4",
                }

            def voice(_text, path):
                Path(path).write_bytes(b"audio")

            def download(_url, path):
                Path(path).write_bytes(b"video")

            def prepare(_source, output, _duration):
                Path(output).write_bytes(b"vertical")

            loaded = []
            try:
                create_scene_from_selected_visual(
                    0,
                    scene,
                    plan,
                    visual,
                    create_voice_fn=voice,
                    get_scene_paths_fn=paths,
                    download_video_fn=download,
                    prepare_vertical_video_fn=prepare,
                    load_video_for_scene_fn=lambda *_: loaded.append(True) or _FakeVideo(),
                    create_subtitle_clips_fn=lambda *_args, **_kwargs: [],
                    audio_clip_cls=_FakeAudio,
                    composite_clip_cls=_FakeComposite,
                    verify_rendered_visual_fn=lambda *_args: type(
                        "V", (), {"passed": False, "reason": "bending not visible"}
                    )(),
                )
                assert False, "should have rejected rendered clip"
            except RuntimeError as exc:
                assert "exact rendered clip rejected" in str(exc)
            assert loaded == []
        finally:
            os.chdir(old)
