"""Composition authority for fixed-topic full rehearsal.

Production main.yml only needs to invoke this installer after the existing
observable-opening installer. The installer applies the flap projection and
then runs the API-free full-path rehearsal against the final composed files.
"""
import subprocess
import sys

subprocess.run([sys.executable, "ci_fixed_topic_flap_opening_hotfix.py"], check=True)
subprocess.run([sys.executable, "quality/fixed_topic_full_path_rehearsal_test.py"], check=True)
print("FIXED_TOPIC_FULL_REHEARSAL_HOTFIX=PASS")
