from content.script_formal_endings import formalize_existing_question_ending, formalize_script_text


# Exact production counterexample from Run 34480412936 / 34480072012 Scene 2.
# Both runs failed identically on main HEAD 7aacdead07fe0e72d355e6b10e7ad8ef46049fe3
# after exhausting all 3 Script Engine V2 writer attempts on the same
# unformalized question ending.
source = "그런데 비행기 날개 끝의 작은 막대가 왜 필요한가?"
expected = "그런데 비행기 날개 끝의 작은 막대가 왜 필요할까요?"
assert formalize_existing_question_ending(source) == expected
assert formalize_script_text(source) == expected

# The repair is deliberately narrow to the `필요한가?` necessity-question
# family, mirroring the existing `시키는가?` repair. Other plain `-는가?/-ㄴ가?`
# questions remain under their existing (unrepaired) contracts.
assert formalize_existing_question_ending("왜 날개 끝에 막대가 있는가?") == "왜 날개 끝에 막대가 있는가?"
assert formalize_existing_question_ending("정전기 방전기는 어디에 있는가?") == "정전기 방전기는 어디에 있는가?"

# Existing approved question repairs remain unchanged.
assert formalize_existing_question_ending("날개 끝에 막대가 있나요?") == "날개 끝에 막대가 있습니까?"
assert (
    formalize_existing_question_ending("그런데 비행기 날개 끝의 작은 막대는 어떻게 공기 흐름을 변화시키는가?")
    == "그런데 비행기 날개 끝의 작은 막대는 어떻게 공기 흐름을 변화시킬까요?"
)

# Declarative narration remains unchanged by the question-only rule.
statement = "정전기 방전기는 날개 끝에 장착됩니다."
assert formalize_script_text(statement) == statement

print("RUN_34480412936_FORMAL_NEED_QUESTION_REGRESSION_PASS")
