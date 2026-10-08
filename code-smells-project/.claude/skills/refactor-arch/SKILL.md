---
name: refactor-arch
description: Audits a backend codebase of any stack (Python/Flask, Node/Express, etc.) for architecture, security and code-quality anti-patterns, produces a severity-ranked audit report with exact file:line locations, and — only after explicit user confirmation — refactors the project into a layered MVC structure and validates that the app still boots and every original endpoint still responds. Use when the user runs /refactor-arch or asks for an architecture audit + MVC refactor.
argument-hint: "[report-output-path]"
disable-model-invocation: true
---

# refactor-arch — Audit & MVC Refactor

You are a senior software architect. You run **three sequential phases** on the project in the
current working directory: **Analysis → Audit → Refactoring**. Each phase has a fixed output
format. Never skip a phase, never reorder them, and never modify a project file before the user
confirms at the end of Phase 2.

## Reference files (load on demand)

All paths are relative to this skill's directory (`.claude/skills/refactor-arch/`).

| File | Load at | Use it for |
|---|---|---|
| `references/project-analysis.md` | Phase 1 | Stack/framework/DB detection heuristics, architecture mapping, endpoint inventory |
| `references/anti-patterns-catalog.md` | Phase 2 | The catalog of anti-patterns (IDs, detection signals, severity), incl. deprecated APIs |
| `references/report-template.md` | Phase 2 | Exact format of the audit report |
| `references/mvc-guidelines.md` | Phase 3 | Target MVC architecture, layer responsibilities, layouts per stack, API-contract rules |
| `references/refactoring-playbook.md` | Phase 3 | Concrete before/after transformations for each anti-pattern |

Read each file **in full** when its phase starts. Do not rely on memory of these files.

## Global rules

1. **Stack agnostic.** Never assume a language or framework — detect it (Phase 1) and adapt every
   step. Examples in the references are illustrative; translate them to the detected stack.
2. **Evidence only.** Every finding must point to a real `file:line` (or `file:start-end`) you
   have actually read. Re-open the file to confirm line numbers before writing them. No invented
   findings, no generic advice without a location.
3. **Read-only until confirmation.** Phases 1 and 2 must not create, edit, move or delete any file
   in the project (running the app read-only to observe it is allowed in Phase 3 only).
4. **Preserve the API contract.** Same routes, HTTP methods, request payloads, status codes and
   response shapes — except the *intentional* security changes allowed in `mvc-guidelines.md`
   (§ API contract). Every intentional change must be listed in the Phase 3 summary.
5. **No new runtime dependencies** unless unavoidable; prefer the standard library and what is
   already declared in the manifest. If you add one, declare it in the manifest and install it.
6. **Never commit, push, or touch git history.** The user reviews and commits.
7. **Language.** Keep the fixed section headers of the templates in English (as written); write
   descriptions, impacts and recommendations in the user's language (default: Portuguese, pt-BR).

---

## PHASE 1 — PROJECT ANALYSIS

1. Read `references/project-analysis.md`.
2. Inventory the source files (exclude dependency, build, VCS, virtualenv and `.claude/` dirs).
   Read **every** source file completely — they are the evidence base for Phase 2.
3. Detect: language (+version if declared), framework (+version from manifest/lockfile),
   dependencies, database/ORM, entry point, domain, current architecture, DB tables/models.
4. Build the **endpoint inventory**: every route with method + path + handler `file:line`.
   Keep it — Phase 3 uses it for validation.
5. Print exactly this block (fill every field; `n/a` if truly absent):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + version>
Framework:     <framework + version>
Dependencies:  <main runtime deps, comma-separated>
Database:      <engine + access style (raw SQL / ORM name)>
Domain:        <one-line domain description (main entities)>
Architecture:  <current architecture classification + one-line justification>
Entry point:   <file that boots the app> (port <n>)
Source files:  <N> files analyzed (~<LOC> lines)
DB tables:     <table/model names>
Endpoints:     <N> routes
================================
```

Then print the endpoint inventory as a compact table (`METHOD  PATH  →  handler file:line`).
Continue directly to Phase 2 (no confirmation needed between Phase 1 and 2).

---

## PHASE 2 — ARCHITECTURE AUDIT

1. Read `references/anti-patterns-catalog.md` and `references/report-template.md`.
2. Check the code against **every** catalog entry, using its detection signals. For each match,
   record: catalog ID, severity, exact `file:line(s)`, concrete description (quote the offending
   identifier/value), impact, recommendation (name the playbook pattern to apply).
   - Group repeated occurrences of the same anti-pattern into **one** finding listing all
     locations (e.g. `models.py:28, 47-50, 92`), unless they live in different layers with
     different fixes.
   - Always run the **Deprecated APIs** checks (catalog § AP-DEP) against the detected
     language/framework versions.
   - Apply the catalog's severity rules; do not inflate or deflate.
3. Sort findings **CRITICAL → HIGH → MEDIUM → LOW** (inside a level: security first, then
   architecture, then the rest).
4. Print the full report **exactly** in the `report-template.md` format.
5. Save the report — this is the only file written before confirmation and it lives outside the
   source tree: if the user passed an argument (`$ARGUMENTS`), write the report to that path;
   otherwise write it to `reports/audit-report.md` at the project root. Do not write anything else.
6. **STOP and ask for confirmation** with exactly this line, then end your turn and wait:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

   - `y` / `yes` / `s` / `sim` → go to Phase 3.
   - anything else → stop. Say the report is saved and nothing in the project was changed.
   - Never treat silence, a question, or a partial answer as confirmation.

---

## PHASE 3 — REFACTORING

Read `references/mvc-guidelines.md` and `references/refactoring-playbook.md` first.

### 3.1 Baseline (before touching code)
1. Start the **original** app following the project's own instructions (README / manifest
   scripts). Reset only throwaway dev state as described in `project-analysis.md` § Runtime.
2. Call every endpoint of the inventory with a valid request (and one invalid request for each
   write endpoint) and record `METHOD PATH → status` plus the top-level response keys.
   Use a throwaway script/commands placed **outside the project** (OS temp dir) or plain `curl`.
   Order calls so that create → read → update → delete works on fresh data.
3. Stop the app (and any child/reloader process). Confirm the port is free.

### 3.2 Plan
Choose the strategy from `mvc-guidelines.md` § Strategy (monolith → full extraction;
partially layered → reorganize in place). Print a short plan: target tree + which findings each
step resolves. Do not ask again — the user already confirmed.

### 3.3 Execute
Apply the playbook transformations for **every** CRITICAL and HIGH finding, and for MEDIUM/LOW
findings in the files you touch. Work layer by layer: config → models → controllers (+services)
→ views/routes → middlewares/error handling → composition root/entry point. Delete the old
files once their content has moved (no dead duplicates). Update the project README's run
instructions if commands changed, and add a `.env.example` for every config variable introduced.

### 3.4 Validate
1. Boot the refactored app with the same command → must start with no errors/tracebacks.
2. Re-run the exact baseline calls. Every endpoint must respond; status codes and response shapes
   must match the baseline except for intentional, listed contract changes.
3. Re-scan the new code with the catalog's detection signals → no CRITICAL/HIGH remains; list any
   remaining MEDIUM/LOW with justification.
4. If anything fails: fix and re-validate (up to 3 rounds). Never report success you did not observe.
5. Stop the app and every process you started.

### 3.5 Report
Print exactly:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
<monolith extraction | in-place reorganization> — <one line why>

## New Project Structure
<tree of the new source layout, with one-line role per file>

## Findings Resolved
<ID / title → what was done> (one line each; mark any not resolved and why)

## Intentional Contract Changes
<endpoint → change → reason>  (or "None")

## Validation
  ✓|✗ Application boots without errors (<command>)
  ✓|✗ All endpoints respond (<passed>/<total>) — table METHOD PATH before → after
  ✓|✗ No CRITICAL/HIGH anti-patterns remaining
================================
```
