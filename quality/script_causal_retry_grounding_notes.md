# Script causal retry production counterexample

Production run 32555499826 reached a valid aviation Winner and Candidate Gate PASS, then exhausted all 5 bounded script attempts. Four attempts failed `Causal Information Progression` with mechanism paraphrase/elaboration without a new causal step; one attempt produced only 7 scenes for a design topic requiring at least 8.

This hotfix keeps validator thresholds, retry count, API budget, cost ceiling, and Sora policy unchanged. It preserves already-grounded aviation specificity fields through `validate_candidate()` so the script writer can build distinct causal units from verified candidate evidence, and gives targeted retry guidance for the exact production failures.
