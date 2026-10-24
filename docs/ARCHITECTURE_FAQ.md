# Architecture FAQ — Data Pipeline Immune System

### Q1: Why not rely 100% on LLMs for diagnosis?
LLMs are probabilistic and introduce latency (2-4 seconds) and API costs. Known deterministic failures (e.g. transient task timeouts, missing foreign keys) are resolved instantly (50ms) by the deterministic rules engine.

### Q2: How does the Never-Allow boundary work?
Even if an AI model recommends an action like `DROP TABLE` with a confidence score of 1.0, the Python `NeverAllowViolation` interceptor hard-blocks execution before any database call is dispatched.

### Q3: Where are secrets kept?
All production credentials reside in Google Cloud Secret Manager. Local development secrets reside in `.env`, which is strictly excluded from version control by `.gitignore`.
