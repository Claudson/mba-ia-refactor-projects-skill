# Audit Report Template (Phase 2)

The report is printed to the user **and** saved as Markdown (see SKILL.md, Phase 2 step 5).
Reproduce the structure below exactly. Replace `<...>`; keep headers, separators and field
labels verbatim (English). Free text (descriptions, impact, recommendation) in the user's language.

## Rules
1. Findings sorted **CRITICAL → HIGH → MEDIUM → LOW**; inside a level: security, then
   architecture, then others. Number them sequentially (`F01`, `F02`, …).
2. `File:` must hold exact locations: `path:line`, `path:start-end`, or several separated by
   `, ` — paths relative to the project root. Multiple files → one `File:` line per file.
3. Every finding references a catalog ID (`AP-xx` / `AP-DEP`) and a playbook pattern (`P-xx`).
4. *Description* quotes the concrete offending code/value (identifier, literal, query).
5. Summary counts must equal the number of findings listed per level, and `Total` the sum.
6. The **Deprecated APIs** section is mandatory, even if empty ("none detected for …").
7. No finding without evidence; no duplicated finding.

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project folder name>
Stack:   <language + version> + <framework + version> (<database / access style>)
Files:   <N> analyzed | ~<LOC> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | <title> | AP-xx | <first file:line> |
| ... | | | | |

## Findings

### F01 [CRITICAL] <Title>
File: <path:lines>
Catalog: AP-xx — <catalog name>
Description: <what is wrong, quoting the offending code>
Impact: <concrete consequence in this project>
Recommendation: <what to do> (Playbook P-xx)

### F02 [HIGH] <Title>
File: <path:lines>
Catalog: AP-xx — <catalog name>
Description: ...
Impact: ...
Recommendation: ... (Playbook P-xx)

<... one block per finding ...>

## Deprecated APIs
| Location | Deprecated usage | Modern equivalent |
|---|---|---|
| <path:line> | <call> | <replacement> |
<or: "None detected for <stack + versions>.">

## Architecture Notes
- Current: <architecture label from Phase 1> — <why>
- Missing layers: <config | models | controllers | views/routes | error handling | composition root>
- Proposed target: <one-line summary of the MVC target structure>

================================
Total: <N> findings
================================
````

## Example finding (for calibration)

```markdown
### F02 [CRITICAL] SQL Injection
File: models.py:28, 47-50, 110
Catalog: AP-02 — SQL Injection
Description: Queries montadas por concatenação: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
Impact: `POST /login` com email `' OR 1=1 --` autentica sem senha; qualquer tabela pode ser lida ou apagada.
Recommendation: Usar queries parametrizadas (`?` + tupla de parâmetros) em todo acesso a dados (Playbook P-02).
```
