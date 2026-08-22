from analytics import COLLECTION_STATES, SCHEMA_VERSION

assert SCHEMA_VERSION == 1
assert {"pending", "partial", "complete", "unavailable"} == set(COLLECTION_STATES)
print("ANALYTICS FEEDBACK CONTRACT IMPORT: PASS")
