# Documentation Rules — Data Pipeline Immune System

What to document, where to put it, and how to write it. Short version: document things that aren't obvious from reading the code, and keep it maintained.

---

## What gets documented

### Always document:
- Agent responsibilities, inputs, outputs, permissions, and failure behaviour (`docs/architecture/agent-architecture.md` and `.agents/rules/agent-rules.md`)
- Every automated remediation action (what it does, what safety conditions apply, rollback strategy)
- Failure injection scenarios (what failure is simulated, expected immune response)
- Significant architectural decisions (`docs/decisions/decision.md`)
- Environment differences between dev/staging/production
- Deployment process (so it can be reproduced from scratch)
- Operational procedures: incident response, escalation, troubleshooting

### Document if it's non-obvious:
- Configuration options and their effects
- Why a specific threshold or algorithm was chosen
- Why a particular approach was rejected
- Known limitations of a component

### Skip documentation for:
- Self-evident code with clear variable names
- Standard library usage
- Trivial getters/setters

---

## Where docs live

```
docs/
├── architecture/
│   ├── system-architecture.md   Overall system design
│   ├── agent-architecture.md    Agent design and communication
│   ├── data-flow.md             Data movement through the system
│   └── failure-recovery.md      How the system recovers from each failure type
│
├── decisions/
│   └── decision.md              All ADRs in one file (indexed)
│
├── operations/
│   ├── runbook.md               Setup, deployment, and operational procedures
│   ├── incident-response.md     What to do when the immune system itself fails
│   └── troubleshooting.md       Common problems and how to debug them
│
└── security/
    └── security-model.md        IAM, secrets, data sensitivity, audit

flow.md                          How data and control flow through the system (kept at docs/ root)
```

---

## Documentation style

Write like a developer who built the system, not like a marketing document.

**Write in Indian English / English (India).** Natural, direct, technically accurate. Not overly formal.

**Explain the why.** "We use z-score instead of percentage threshold" should be followed by why, not just stated as fact.

**Be honest about limitations.** "The adaptive baseline is unreliable for pipelines with fewer than 14 historical runs" is useful. Hiding limitations is not.

**Avoid:**
- Excessive headings for short sections
- Repeating what the code clearly shows
- Corporate-sounding language ("leverage", "synergy", "robust solutions")
- AI-generated filler text that says nothing

**Prefer:**
- Concrete examples over abstract descriptions
- ASCII diagrams for flows and architecture
- Tables for comparative information
- Short paragraphs

---

## Keeping docs up to date

When you change a component:
1. Update the relevant doc section immediately (not "later")
2. Update `flow.md` if the data or control flow changed
3. Add or update an ADR in `decision.md` if the change was a significant design choice
4. Update the runbook if the operational procedure changed

The PR checklist includes a documentation section. If a PR changes significant behaviour without a docs update, it should not be merged.

---

## Comments in code

Comments must explain **why**, not **what**. The code already shows what.

Good places for comments:
- Safety checks (why is this check here?)
- Confidence score calculations (why these weights?)
- Adaptive baseline algorithm (why this lookback window?)
- Never-allow rule enforcement (why is this specific to code and not the rules file?)
- Any place where the obvious implementation was rejected in favour of something less obvious

Bad places for comments (delete these if you see them):
```python
# loop through results
for result in results:

# return the value
return value
```

---

## ADR process

Write an ADR when:
- A significant architectural choice was made that would confuse someone reading the code later
- A reasonable alternative was rejected (and the reason should be recorded)
- A design changed significantly from the original plan

Do not write an ADR for:
- Minor implementation choices
- Library version selection (unless there's a specific conflict)
- Internal function naming

ADRs live in `docs/decisions/decision.md` as a flat list, not separate files. This keeps them easier to browse.

---

*Last updated: 2026-10*
