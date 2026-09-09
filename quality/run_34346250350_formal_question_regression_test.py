from content.script_formal_endings import formalize_existing_question_ending, formalize_script_text


# Exact production counterexample from Run 34346250350 Scene 2.
source = "그런데 비행기 날개 끝의 작은 막대는 어떻게 공기 흐름을 변화시키는가?"
expected = "그런데 비행기 날개 끝의 작은 막대는 어떻게 공기 흐름을 변화시킬까요?"
assert formalize_existing_question_ending(source) == expected
assert formalize_script_text(source) == expected

# The repair is deliberately narrow to the explanatory `어떻게 ...시키는가?`
# family. Other plain questions remain under their existing contracts.
assert formalize_existing_question_ending("왜 날개 끝에 막대가 있는가?") == "왜 날개 끝에 막대가 있는가?"
assert formalize_existing_question_ending("정전기 방전기는 어디에 있는가?") == "정전기 방전기는 어디에 있는가?"

# Existing approved question repair remains unchanged.
assert formalize_existing_question_ending("날개 끝에 막대가 있나요?") == "날개 끝에 막대가 있습니까?"

# Declarative narration remains unchanged by the question-only rule.
statement = "정전기 방전기는 날개 끝에 장착됩니다."
assert formalize_script_text(statement) == statement

print("RUN_34346250350_FORMAL_QUESTION_REGRESSION_PASS")
