# Script opening lock hotfix

Production failure evidence showed repeated Script API retries after a Hook had already been approved. This hotfix keeps the existing quality and budget gates, but restores the approved `micro_narrative.hook` and `micro_narrative.core_question` into Scene 1 and Scene 2 before validation.

The Script model still supplies visual metadata for those scenes and writes the explanatory body. A narrow deterministic whitelist repairs a few safe Korean sentence-ending variants before the existing speech-style validator runs. Unrecognized wording remains unchanged and therefore still fails closed through the existing bounded retry path.
