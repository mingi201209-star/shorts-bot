# Aviation specificity output repair

- Applies only when `SHORTS_CANDIDATE_SCOPE=aviation`.
- Candidate Gate thresholds and implementation remain unchanged.
- A `SELECTED` winner must carry at least one grounded specificity field.
- If all specificity fields are omitted, one bounded schema-repair call is allowed through the existing budget guard.
- Repair may only copy/summarize a concrete element already present in the original Candidate JSON.
- Repair must return `REGENERATE` rather than invent a new fact, number, causal claim, design intent, or historical origin.
- Non-aviation runs never invoke this repair path.
