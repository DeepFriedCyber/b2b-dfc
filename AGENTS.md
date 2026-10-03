# AGENTS.md

Operating contract for coding agents working on **B2B DFC**.

- Repository: `b2b-dfc`
- Python package: `b2b_dfc`
- Source root: `src/`
- Tests: `tests/`
- Product may be referred to conceptually as the **DFC Platform**.
- Current milestone: **Industry Intelligence Layer v0.01** (see `docs/industry-intelligence-v0.01.md`)

---

## 1. Core product principle

**Understand first. Retrieve second. Verify third.**

These are three distinct stages. Collapsing them into a single LLM call is a design defect.

The system must be able to distinguish between:

1. **Meaning** — what the user actually intends.
2. **Concepts** — which controlled industry concepts correspond to that meaning.
3. **Retrieval** — what information can be retrieved.
4. **Evidence** — what factual claims can be supported by evidence.

A resolution to a concept is not evidence of anything about a company or product.
A retrieval result is not a verified claim.

---

## 2. Initial domains

Two domain values only:

- `CYBERSECURITY`
- `AI`

A concept carries **`domains` — a list of one or more domain values**.

Cross-domain concepts use multiple entries: `domains = [CYBERSECURITY, AI]`. Do **not**
create a separate intersection domain (for example `CYBERSECURITY_AND_AI`) merely to
represent the overlap.

Do **not** introduce a generic "Technology" domain. Generic-domain dumping destroys the
value of controlled terminology and is a review-blocking error.

---

## 3. Development methodology

Test-driven and benchmark-driven development.

For any behavioural change:

1. Write or update the test first.
2. Confirm the expected behaviour is expressed and currently unmet.
3. Implement the smallest appropriate change.
4. Run the relevant tests.
5. Run the complete suite.

**Never modify benchmark expectations in order to make an implementation pass.**
A failing benchmark assertion is information about the implementation, not about the benchmark.

---

## 4. Deterministic first

Industry Intelligence v0.01 must **not** depend on:

- OpenAI
- Ollama
- Qwen
- Transformers
- embeddings
- vector databases
- agent frameworks

unless explicitly requested in a later milestone. If a task appears to require one of these,
stop and raise the conflict rather than adding the dependency.

---

## 5. Ontology / evidence boundary

Ontology relationships describe **concepts**. They do **not** establish facts about
companies or products.

```
MDR MAY_USE EDR
```

does **not** mean:

```
Vendor X's MDR includes EDR.
```

Likewise:

```
MDR MAY_PROVIDE Incident Response
```

must **never** automatically satisfy a user's requirement for incident response.
`MAY_PROVIDE` is not `PROVIDES`.

Entity and product claims require evidence. Absence of evidence must be represented
honestly, not silently inferred from taxonomy.

### 5.1 Concept lifecycle and maturity

`status` is a lifecycle state: `ACTIVE`, `CANDIDATE`, `REJECTED`, `DEPRECATED`, `MERGED`.

Normal deterministic resolution treats **only `ACTIVE` concepts as canonical and
resolvable**. A `CANDIDATE` concept must never silently behave as a canonical concept.
`DEPRECATED` and `MERGED` concepts must not seed search expansion. Support for historical
or deprecated mappings may be added in a later milestone, not assumed in v0.01.

`terminology_maturity` is ontology metadata. It does **not** affect deterministic
resolution behaviour in v0.01. Later milestones may use it for ontology curation, search
presentation or ranking.

### 5.2 No concepts for acronyms

Do not create a separate canonical concept merely because an acronym exists.

```
MDR   is an alias of  Managed Detection and Response
SOC   is an alias of  Security Operations Center   (where appropriate)
```

Never create duplicate or near-duplicate concepts to satisfy a numerical target.

---

## 6. Search expansion

Graph connectivity must **not** automatically become query expansion.

Every relationship carries an explicit search policy:

| Policy | Meaning |
| --- | --- |
| `SAFE` | Expansion is safe for retrieval without further checks. |
| `CONSERVATIVE` | Expansion permitted only under narrow conditions; may require confirmation. |
| `DISCOVERY_ONLY` | Permitted for discovery/suggestion only — never silently added to a retrieval query. |
| `NONE` | Must never be used for expansion. |

**False semantic expansion is a serious defect**, not a ranking nuisance. Over-expansion
is treated as a correctness failure and is measured explicitly (see §9 and the v0.01 spec).

---

## 7. Clarify rather than assume

Interpretation is explicit and always in one of three states:

- `RESOLVED` — direct terminology, or sufficiently strong contextual evidence, removes
  material ambiguity.
- `ASSUMED` — one interpretation is substantially better supported by the context, but
  material ambiguity technically remains.
- `CLARIFY` — multiple plausible interpretations remain, and selecting between them could
  materially change the result.

When ambiguity materially affects results, prefer clarification over guessing. `ASSUMED` is
a legitimate outcome, but it is never silent: the assumption is recorded in the structured
output and identifies the concept that was assumed.

### 7.1 Initial regression cases

These are the **initial** regression cases, not universal linguistic rules:

| Query | State | Reading |
| --- | --- | --- |
| `MCP training` | `CLARIFY` | Model Context Protocol? Training *about* MCP? Training a model *for* MCP use? |
| `MCP server security` | `RESOLVED` | Model Context Protocol |
| `latest MCP developments in AI agents` | `ASSUMED` | Model Context Protocol |

### 7.2 Alias type is not ambiguity

Alias types are `EXACT_ALIAS`, `ABBREVIATION`, `COMMON_NAME`, `MARKET_TERM`, `LEGACY_TERM`,
`MISSPELLING`.

There is no `AMBIGUOUS_ALIAS` type. Ambiguity is represented **separately** from alias
type. Conceptually an alias contains: alias text, alias type, one or more candidate concept
IDs, and an `ambiguous` boolean.

```
MCP:  alias_type = ABBREVIATION
      candidate   = model_context_protocol
      ambiguous   = true
```

The architecture must permit multiple candidates in future.

---

## 8. Inspectable interpretation

Important interpretations must remain **structured and inspectable** so a future user
interface can display them and let the user correct them.

The architecture must not immediately reduce the user's request to an opaque embedding or a
generated answer. If a human cannot see and correct what the system believed the user meant,
the design is wrong.

---

## 9. Benchmark integrity

Negative assertions such as `must_not_infer` are **first-class requirements**.

Do not remove, weaken, or relax them to improve benchmark scores. Deleting a
`must_not_infer` case because the implementation fails it is a regression in the
benchmark, not progress in the implementation.

---

## 10. Coding approach

Prefer:

- standard Python library;
- `dataclasses` and `enum` where appropriate;
- explicit type annotations;
- small, single-purpose modules;
- deterministic behaviour;
- pure functions where practical;
- JSON for the initial ontology data;
- readable tests that state intent;
- minimal dependencies.

Avoid premature:

- graph databases;
- vector databases;
- microservices;
- distributed systems;
- orchestration frameworks;
- agent frameworks.

---

## 11. Development environment

- Windows
- VS Code
- Windows PowerShell
- Python 3.11+
- `.venv` (project virtual environment)
- pytest

All terminal commands **must be PowerShell-compatible**. Never assume Bash.

Do not use:

- `&&`
- `mkdir -p`
- `ls -la`
- Bash heredocs

Prefer file-editing tools for source, configuration, and data files instead of generating
file contents through the terminal.

Standard commands:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

---

## 12. Scope discipline

If a task would require ontology concepts, aliases, relationships, benchmark data, models,
a resolver, ambiguity handling, LLM dependencies, embeddings, or a vector database
**outside an explicitly requested milestone**, stop and confirm scope first.

Do not commit or push to Git unless explicitly instructed.