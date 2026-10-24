# Chaos Engineering & Immune Drill Playbook
Run monthly chaos drills against the staging environment:
1. `python3 failure_injection/null_spike.py` -> Verify QuarantineHandler captures nulls.
2. `python3 failure_injection/api_failure.py` -> Verify exponential backoff retry.
3. `python3 failure_injection/schema_drift.py` -> Verify P1 approval state trigger.
