from content.script_formal_endings import formalize_declarative_text, formalize_script_text


# Exact production counterexample from Run 34463253519 (main HEAD
# bf2ef7adb30fcfa3bc3a6a82d9e350c8e0446147), which exhausted all 3 Script
# Engine V2 writer attempts on the same unformalized declarative ending.
source = "비행기가 이륙할 때 날개 뒤쪽 플랩이 펼쳐진다."
expected = "비행기가 이륙할 때 날개 뒤쪽 플랩이 펼쳐집니다."
assert formalize_declarative_text(source) == expected
assert formalize_script_text(source) == expected

# The repair is deliberately narrow to the exact `펼쳐진다` corpus item,
# matching the existing one-word-at-a-time style of this table (e.g.
# `달라진다`, `좋아진다`). Unrelated `-진다` predicates remain unchanged so
# this stays a corpus addition, not a broad morphology rewrite.
untouched = "소용돌이가 이쪽으로 몰려진다."
assert formalize_declarative_text(untouched) == untouched

# Existing production question contract is unaffected by the declarative fix.
question = "왜 날개 뒤쪽 플랩이 펼쳐질까요?"
assert formalize_script_text(question) == question

print("RUN_34463253519_FORMAL_FLAP_DECLARATIVE_REGRESSION_PASS")
