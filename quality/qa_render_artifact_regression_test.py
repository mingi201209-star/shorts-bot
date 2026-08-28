from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    workflow = (ROOT / ".github/workflows/main.yml").read_text(encoding="utf-8")

    assert "Preserve verified production artifact" in workflow
    assert "Preserve QA-only render artifact" in workflow
    assert "production-qa-render-${{ github.run_id }}" in workflow
    assert "failure()" in workflow
    assert "hashFiles('final_shorts_*.mp4')" in workflow
    assert "NOT_UPLOAD_APPROVED" in workflow
    assert "DIRECTOR_HOLD" in workflow
    assert "qa_render_status.json" in workflow
    assert "final_director_qa.json" in workflow
    assert "visual_diversity_preflight.json" in workflow

    # Verified artifact remains success-path only; QA artifact is the failure-path
    # copy and must not change publish semantics.
    verified = workflow.split("- name: Preserve verified production artifact", 1)[1].split("- name:", 1)[0]
    assert "if: always()" not in verified
    qa = workflow.split("- name: Preserve QA-only render artifact", 1)[1].split("- name:", 1)[0]
    assert "failure()" in qa
    assert "final_shorts_*.mp4" in qa

    publish = workflow.split("- name: Publish to YouTube and persist lineage", 1)[1]
    assert "if: always()" not in publish
    assert "ENABLE_YOUTUBE_UPLOAD: ${{ inputs.youtube_upload && '1' || '0' }}" in publish

    # A render-before-failure is required for QA MP4 preservation. Pre-render
    # failures therefore keep diagnostics only because hashFiles is empty.
    assert "if: ${{ failure() && hashFiles('final_shorts_*.mp4') != '' }}" in workflow

    print("DIRECTOR HOLD QA RENDER ARTIFACT REGRESSION: PASS")


if __name__ == "__main__":
    main()
