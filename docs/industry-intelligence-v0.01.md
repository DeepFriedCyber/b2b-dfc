# Industry Intelligence Layer — Specification v0.01

Status: **Specification only.** No implementation exists yet for this milestone.
Repository: `b2b-dfc` · Package: `b2b_dfc`

---

## 1. Purpose and research question

The Industry Intelligence Layer is the understanding stage of the DFC Platform. It exists to
translate ordinary professional language — the way practitioners, buyers and analysts
actually write — into a controlled, inspectable set of industry concepts, while explicitly
detecting ambiguity and refusing to expand meaning it cannot justify.

**Research question:**

> Can ordinary Cybersecurity and AI language be reliably translated into controlled
> industry concepts while explicitly detecting ambiguity and avoiding false semantic
> expansion?

This is an *experiment*, not a finished product. Success is measured, not asserted.

### 1.1 What this milestone deliberately is not

- Not a search engine.
- Not an answer generator.
- Not a vendor evaluation or comparison product.
- Not an evidence system.
- Not an LLM wrapper.

### 1.2 Non-goals

- No retrieval, ranking or corpus of documents.
- No evidence verification, provenance or citation.
- No vendor/company/product fact base.
- No embeddings, vector store, graph database or agent framework.
- No generic "Technology" domain.

---

## 2. Pipeline

```
Natural-language query
        │
        ▼
Terminology Resolver
        │
        ▼
Cybersecurity + AI Ontology
        │
        ▼
Ambiguity Gate  ──►  RESOLVED  /  ASSUMED  /  CLARIFY
        │
        ▼
Structured QueryPlan
```

Stage-by-stage:

| Stage | Responsibility |
| --- | --- |
| **Natural-language query** | Raw input, preserved verbatim. |
| **Terminology Resolver** | Match user wording (labels, aliases, acronyms, buyer language) to candidate concepts. Detects unknown terminology. Produces candidates with evidence-of-match (which term matched), not just a score. |
| **Ontology** | The controlled concept store: concepts, aliases, relationships, and their search policies. Concepts only — no companies, products or claims. |
| **Ambiguity Gate** | Decides whether the resolution is unambiguous, resolvable-under-assumption, or requires clarification. Applies search policy to any proposed expansion. |
| **QueryPlan** | The inspectable structured output described in §7. |

### 2.1 Explicitly out of scope for v0.01

Retrieval and evidence verification are **later stages**. v0.01 ends at the QueryPlan.
A QueryPlan is not a search query to be executed and not a claim about any vendor.

### 2.2 Ordering guarantees

- The Ambiguity Gate runs **after** candidate resolution and **before** any expansion is
  accepted into the QueryPlan.
- Expansion never happens implicitly during graph traversal. Traversal produces
  *candidates*; the search policy plus the Ambiguity Gate decide what enters the plan.
- Unknown terminology (§6) never silently becomes a canonical concept.

---

## 3. Domain scope

Two domain values only:

- `CYBERSECURITY`
- `AI`

A concept belongs to **one or more domains**. The field is therefore `domains` — a list
with at least one entry.

| Concept | `domains` |
| --- | --- |
| Managed Detection and Response | `[CYBERSECURITY]` |
| Large Language Model | `[AI]` |
| MCP Security | `[CYBERSECURITY, AI]` |
| AI Red Teaming | `[CYBERSECURITY, AI]` |

Cross-domain concepts use multiple entries. Do **not** create `CYBERSECURITY_AND_AI` (or
any similar intersection value) as a separate domain merely to represent the overlap —
that duplicates meaning and splits vocabulary.

A generic `TECHNOLOGY` domain must not be introduced. Controlled terminology loses its
value the moment everything is admitted.

---

## 4. Concept model

A concept is a controlled meaning. Minimum fields for v0.01:

| Field | Type | Meaning |
| --- | --- | --- |
| `concept_id` | string | Stable, canonical, dot-namespaced identifier. The only identifier that may appear in a QueryPlan's resolved set. Never reuse an ID for a different meaning. |
| `preferred_label` | string | The single canonical term. One concept, one preferred label. |
| `definition` | string | Precise enough to distinguish it from its neighbours. |
| `domains` | list of enum | One or more of `CYBERSECURITY`, `AI` (§3). Cross-domain concepts carry multiple entries. |
| `concept_type` | enum | See §4.1. |
| `status` | enum | Lifecycle state. See §4.2. |
| `terminology_maturity` | enum | How settled the surrounding language is: `STABLE`, `ESTABLISHED`, `EMERGING`, `UNSETTLED`. Ontology metadata only — see §4.3. |

Supporting metadata is permitted but must not replace the fields above.

### 4.1 Concept types

Initial vocabulary:

`DISCIPLINE`, `CAPABILITY`, `TECHNOLOGY`, `PRODUCT_CATEGORY`, `SERVICE_CATEGORY`,
`THREAT`, `RISK`, `CONTROL`, `PROTOCOL`, `FRAMEWORK`, `STANDARD`, `CONCEPT`

Notes on the distinctions that matter most:

- `CAPABILITY` is something an organisation or product can *do*. `TECHNOLOGY` is the
  mechanism. A capability may be delivered by several technologies.
- `PRODUCT_CATEGORY` / `SERVICE_CATEGORY` describe what is bought or sold commercially;
  they are still *concepts*, never assertions that any named vendor offers them.
- `THREAT` and `RISK` are distinct: a threat is an adversary or event; a risk is potential
  impact. Do not merge them.
- `CONCEPT` is a deliberate escape hatch for genuine abstractions, not a bin for
  unclassified leftovers.

### 4.2 Concept lifecycle

`status` values:

`ACTIVE`, `CANDIDATE`, `REJECTED`, `DEPRECATED`, `MERGED`

| State | v0.01 behaviour |
| --- | --- |
| `ACTIVE` | Canonical and resolvable. The only state normal deterministic resolution treats as canonical. |
| `CANDIDATE` | Not canonical. Must never silently behave as a canonical concept. |
| `REJECTED` | Never canonical. |
| `DEPRECATED` | Not canonical; must not seed search expansion. |
| `MERGED` | Not canonical; superseded by another concept. Must not seed search expansion. |

Only `ACTIVE` concepts may appear in a QueryPlan's resolved concept set (§7).

Support for historical or deprecated mappings — that is, resolving a retired term to its
successor — may be added in a later milestone. It is not assumed in v0.01, and the
regression cases in §8.2 must not depend on it.

### 4.3 Terminology maturity

`terminology_maturity` is **ontology metadata**. In v0.01 it does **not** affect
deterministic resolution behaviour. It must not gate, reorder or block resolution.

Later milestones may use it for ontology curation, search presentation or ranking. It is
recorded now so that later curation work has a signal available, not because v0.01 needs it.

---

## 5. Aliases

Aliases are **independent records**, not string fields on a concept. A concept may have
many aliases; an alias points at one or more candidate concepts.

### 5.1 Alias record

Conceptually an alias contains four things:

| Element | Meaning |
| --- | --- |
| **alias text** | The term as users write it. |
| **alias type** | From the vocabulary in §5.2. Describes the *nature* of the term, not its resolvability. |
| **candidate concept IDs** | One or more concepts the term could denote. |
| **`ambiguous` boolean** | Whether selecting among those candidates requires disambiguation. |

A more concrete record shape for v0.01:

| Field | Type | Meaning |
| --- | --- | --- |
| `alias_id` | string | Stable identifier. |
| `surface_form` | string | The alias text. |
| `alias_type` | enum | See §5.2. |
| `candidates` | list | Candidate `concept_id`s, with optional per-candidate notes. |
| `ambiguous` | boolean | `true` when more than one reading of this surface form is plausible. |
| `notes` | string | Recorded reasoning, especially for `ambiguous` aliases. |

The architecture must **permit multiple candidates in future**. A single alias record with
several candidates is the supported shape; the design must not assume one alias resolves to
exactly one concept.

### 5.2 Alias types

`EXACT_ALIAS`, `ABBREVIATION`, `COMMON_NAME`, `MARKET_TERM`, `LEGACY_TERM`, `MISSPELLING`

There is **no `AMBIGUOUS_ALIAS` type.** Alias type and ambiguity are orthogonal:

- An `ABBREVIATION` can be unambiguous (`EDR`) or ambiguous (`MCP`).
- A `COMMON_NAME` can be unambiguous or ambiguous.
- Ambiguity is carried by `candidates` + `ambiguous`, never by the type.

Introducing ambiguity as a type would conflate "what kind of word is this" with "can we
resolve it", and would make the two dimensions impossible to evolve independently.

### 5.3 The MCP case — abbreviation with ambiguity

`MCP` is the canonical worked example. It is an `ABBREVIATION` that is ambiguous:

```
MCP:
  alias_type = ABBREVIATION
  candidate   = model_context_protocol
  ambiguous   = true
```

Its real-world readings are:

| Reading | Canonical concept in v0.01 |
| --- | --- |
| Model Context Protocol | `model_context_protocol` |
| Microsoft Certification Program (and similar legacy/regional expansions) | none |
| Multi-Channel Publishing and other trade usages | none |

Because the readings differ even though only one has a canonical concept, `MCP` alone
cannot be resolved on lexical evidence. It requires surrounding context, or clarification.

Ambiguity can also arise *within a single reading*: `MCP training` is ambiguous even once
`MCP` is read as Model Context Protocol (§8).

### 5.4 Other abbreviated terms

Acronyms such as `MDR`, `EDR`, `XDR`, `SIEM`, `SOAR`, `IAM`, `PAM`, `MFA`, `LLM`, `RAG`
are `ABBREVIATION` aliases, typically with one candidate and `ambiguous: false`.

Two constraints apply to all abbreviations:

- An acronym is **never** the reason to create a separate canonical concept. `MDR` is an
  alias of `Managed Detection and Response`; `SOC` is an alias of `Security Operations
  Center` where appropriate.
- An abbreviation must not be auto-expanded to related graph neighbours. Resolving `MDR`
  resolves Managed Detection and Response — nothing else.

---

## 6. Unknown terminology

Terminology that matches no concept and no alias is **unknown terminology**, not a
candidate concept.

Rules:

- Never auto-create a canonical concept from unknown terminology.
- Never silently drop unknown terminology — record it in the QueryPlan as
  `unresolved_terminology` (§7).
- The plan may still be `RESOLVED` for the parts that *are* understood, provided the
  unresolved remainder is surfaced.
- Unknown terminology is not a `CANDIDATE` concept. It may be *proposed* as one later
  (§4.2, §14), but a proposal is not canonical and must not resolve anything in v0.01.
- Canonical ontology changes require human review. Automated proposal of candidates is a
  **later milestone** (Ontology Curator, §14), not v0.01 behaviour.

---

## 7. QueryPlan

The QueryPlan is the deliverable of v0.01 and the input to later stages. It is structured,
deterministic, serialisable and inspectable. A future UI must be able to render it and let
the user correct it.

Required content:

| Field | Meaning |
| --- | --- |
| `original_query` | The user's input, unmodified. |
| `resolved_concepts` | `ACTIVE` canonical `concept_id`s selected, each with the term that justified it. |
| `interpretation_state` | `RESOLVED` \| `ASSUMED` \| `CLARIFY`. |
| `ambiguities` | Each ambiguity: the surface form, the competing readings, and the decision or open question. |
| `unresolved_terminology` | Terms found that the ontology does not cover. |
| `clarification_request` | Present when `interpretation_state` is `CLARIFY`: the specific question and the options a user could pick. |

Additional fields permitted: `domains` (the domain scope of the plan), `suggested_expansions`
(discovery-only, must be marked as not part of the resolved set), `assumptions` (non-empty
when state is `ASSUMED`, and each entry must identify the assumed concept).

### 7.1 QueryPlan invariants

- `RESOLVED` ⟹ direct terminology or sufficiently strong contextual evidence removed
  material ambiguity.
- `ASSUMED` ⟹ at least one recorded assumption, non-empty and identifying the assumed
  concept; material ambiguity technically remains.
- `CLARIFY` ⟹ a non-empty `clarification_request`; the plan must not pretend to be final.
- `resolved_concepts` never contains an ID that is not in the ontology.
- `resolved_concepts` contains **only `ACTIVE`** concepts (§4.2). A `CANDIDATE` concept must
  never appear as if it were canonical.
- Discovery-only suggestions are never silently merged into `resolved_concepts`.
- The plan asserts **nothing** about any company or product.

---

## 8. Ambiguity model

Interpretation is always in exactly one of three states.

### 8.1 State definitions

- **`RESOLVED`** — direct terminology, or sufficiently strong contextual evidence, removes
  material ambiguity.
- **`ASSUMED`** — one interpretation is substantially better supported by the context, but
  material ambiguity technically remains.
- **`CLARIFY`** — multiple plausible interpretations remain, and selecting between them
  could materially change the result.

`ASSUMED` is a legitimate outcome, but it is never silent: the interpretation is recorded
in the structured output and identifies the concept that was assumed.

### 8.2 Initial regression cases

These are the **initial** regression cases, not universal linguistic rules.

| Query | State | Reading |
| --- | --- | --- |
| `MCP training` | `CLARIFY` | Model Context Protocol? Training *about* MCP? Training a model *for* MCP use? |
| `MCP server security` | `RESOLVED` → Model Context Protocol | `MCP server` plus `security` removes the material ambiguity. |
| `latest MCP developments in AI agents` | `ASSUMED` → Model Context Protocol | Context leans strongly to Model Context Protocol, but "latest developments" is loose enough that material ambiguity technically remains. |

They pin behaviour for this benchmark set. They do **not** generalise:

- They are not linguistic rules, and a resolver must not hard-code them.
- A query that resembles `MCP server security` is not thereby `RESOLVED`.
- A query that resembles `latest MCP developments in AI agents` is not thereby `ASSUMED`.
- New benchmark cases must be decided on their own evidence and reviewed, not settled by
  analogy to this trio.

### 8.3 Applying the definitions

- Multiple plausible interpretations remain **and** choosing between them could materially
  change the resolved concept set or the eventual answer → `CLARIFY`.
- Direct terminology, or context strong enough to remove material ambiguity → `RESOLVED`.
- Context makes one interpretation substantially better supported, but the wording does not
  eliminate the alternative → `ASSUMED`, with the interpretation recorded.

Ambiguity that cannot change the resolved concept set is not material and must not cause
an unnecessary `CLARIFY`.

The `RESOLVED` / `ASSUMED` boundary is a judgement about how much ambiguity the context
actually removed. It is not mechanical and it is not uniform across queries — which is
precisely why §8.2 is pinned as regression cases rather than derived from a rule.

---

## 9. Relationships

Relationships describe **concepts only**. They are directional and typed.

Initial vocabulary:

`BROADER`, `NARROWER`, `RELATED`, `PART_OF`, `USES`, `MAY_USE`, `PROVIDES`,
`MAY_PROVIDE`, `APPLIES_TO`, `AFFECTS`, `MITIGATES`, `DETECTS`, `PROTECTS`,
`IMPLEMENTS`, `REQUIRES`

Symmetric pairs (`BROADER`/`NARROWER`) may be stored once and traversed in both directions;
that is a storage decision, not a semantic one.

### 9.1 Relationship record

| Field | Meaning |
| --- | --- |
| `relationship_id` | Stable identifier. |
| `from_concept_id` / `to_concept_id` | Endpoints. |
| `relationship_type` | From the vocabulary above. |
| `search_policy` | See §9.2. Required. |
| `notes` | Justification, especially for `MAY_*` and `DISCOVERY_ONLY`. |

### 9.2 Search policies

| Policy | Meaning |
| --- | --- |
| `SAFE` | Expansion is safe for retrieval without further checks. |
| `CONSERVATIVE` | Expansion permitted only under narrow conditions; may require confirmation. |
| `DISCOVERY_ONLY` | Permitted for discovery/suggestion only — never silently added to a retrieval query. |
| `NONE` | Must never be used for expansion. |

Graph connectivity must **not** automatically become query expansion. Every expansion
must be justified by the traversed edge's search policy.

### 9.3 The ontology/evidence boundary

```
MDR MAY_USE EDR
```

is a statement about concepts. It is **not**:

```
Vendor X's MDR includes EDR.
```

Similarly, `MDR MAY_PROVIDE Incident Response` must **never** automatically satisfy a
user's requirement for incident response. `MAY_PROVIDE` is not `PROVIDES`. Vendor and
product claims require evidence in a later milestone; absence of evidence must be reported
honestly rather than inferred from taxonomy.

---

## 10. Initial ontology scope

**Initial target range: approximately 50–75 concepts.** This is a target, **not** a
mandatory completion requirement. Ontology quality, distinction and usefulness take
precedence over hitting a numerical count. A smaller well-separated ontology is a better
outcome than a padded one.

The list below is a **seed for review**, not a specification to be generated blindly. It
must be reviewed for: correct type assignment, correct `MAY_*` vs definitive verbs,
explicit search policies, and no generic-domain dumping.

Note that many seed entries are *acronyms* rather than concepts — `MDR`, `EDR`, `SOC`,
`IAM`, `LLM`. Those become aliases of canonical concepts, not concepts in their own right.

### Security Operations

`MDR`, `EDR`, `XDR`, `SOC`, `SIEM`, `SOAR`, `Threat Hunting`, `Incident Response`,
`Security Operations Center`, `Managed Detection and Response`, `Security Automation`,
`Log Analytics`, `Threat Detection`, `Threat Intelligence`, `Digital Forensics`,
`Vulnerability Management`, `Penetration Testing`

### Identity

`IAM`, `Authentication`, `Authorization`, `PAM`, `MFA`, `Machine Identity`,
`Non-Human Identity`, `Least Privilege`, `Privileged Access`, `Identity Provider`,
`Directory Services`, `Identity Governance`

### AI

`LLM`, `Foundation Model`, `AI Agent`, `RAG`, `Embeddings`, `Vector Search`,
`Reranking`, `Model Context Protocol`, `MCP Server`, `MCP Client`, `MCP Host`,
`AI Governance`, `Model Training`, `Inference`, `Prompt`, `Multimodal Model`

### AI Security

`AI Security`, `Agent Security`, `MCP Security`, `Prompt Injection`,
`Indirect Prompt Injection`, `Excessive Agency`, `AI Red Teaming`, `Guardrails`,
`Agent Identity`, `Agent Authorization`, `Data Poisoning`, `Model Supply Chain`,
`Sensitive Information Disclosure`, `Agentic AI`

### 10.1 No concepts for acronyms

An acronym is not a concept. `MDR` **is** Managed Detection and Response; `SOC` **is** an
alias of Security Operations Center where appropriate. Neither earns a canonical concept
by virtue of being short.

Avoid duplicate and near-duplicate concepts created solely to satisfy the target count. If
the reviewed ontology lands below 50 because the distinctions are cleaner, that is a
correct result.

### 10.2 Ontology review checklist

Before any concept set is accepted:

1. Does every concept have all §4 fields, including `terminology_maturity`?
2. Is every concept assigned via `domains` to `CYBERSECURITY` and/or `AI` only — no
   `TECHNOLOGY`, no intersection pseudo-domain?
3. Are `preferred_label` values unique per concept and unambiguous against each other?
4. Is every relationship's search policy set deliberately rather than defaulted?
5. Are vendor- or product-shaped terms excluded as concepts?
6. Are duplicate and near-duplicate candidates merged?
7. Does any acronym have a canonical concept of its own that merely duplicates a spelled-out
   concept? If so, demote it to an alias.
8. Are deprecated/legacy terms present only as `LEGACY_TERM` aliases?
9. Does any concept exist purely to absorb an unclassifiable leftover, or purely to reach
   the target count? If so, remove it.

---

## 11. Benchmark

Target: approximately **100 queries**, deterministic, version-controlled.

Coverage categories:

1. Canonical terminology.
2. Aliases and acronyms.
3. Natural buyer language.
4. Ambiguous terminology.
5. Emerging and marketing terminology.
6. Negative and adversarial cases.

### 11.1 Record fields

| Field | Meaning |
| --- | --- |
| `query_id` | Stable identifier. |
| `query` | The input text. |
| `category` | One of the six categories above. |
| `expected_concepts` | Canonical `ACTIVE` IDs that must be resolved. |
| `acceptable_related` | Evaluation/discovery metadata — see §11.2. May be empty. |
| `must_not_infer` | Concepts that must **not** be produced — including via expansion. |
| `expected_state` | `RESOLVED` \| `ASSUMED` \| `CLARIFY`. |
| `expected_interpretation` | Required when `expected_state` is `ASSUMED`. See §11.3. |

The §8.2 MCP cases are pinned regression cases.

### 11.2 `acceptable_related`

`acceptable_related` is **evaluation and discovery metadata only**. It is not part of the
expected resolved set.

- It may be **empty**. Empty is the normal case and must not be treated as missing data.
- A concept listed in `acceptable_related` **does not satisfy `expected_concepts`**. It is
  tolerated if it also appears; it is never a substitute for a required concept.
- It never converts a `must_not_infer` concept into an acceptable one. The two fields are
  independent.

### 11.3 Grading an `ASSUMED` case

For a benchmark record with `expected_state = ASSUMED`, the record must identify the
**expected concept interpretation** — the concept the resolver is expected to settle on.
Store it in `expected_interpretation`.

Grading rules:

- The assumption or interpretation field in the QueryPlan must be **non-empty** and must
  **identify the assumed concept** (by `concept_id`).
- **Generated explanatory prose is not graded verbatim.** Wording, phrasing and length are
  free. Only the presence of a recorded assumption and the concept it names are graded.
- The assumed concept must match `expected_interpretation`, and must not appear in
  `must_not_infer`.

This keeps `ASSUMED` cases gradable without freezing natural-language output, which would
otherwise make benchmark maintenance a redaction exercise.

### 11.2 Benchmark integrity

`must_not_infer` is a first-class requirement. Removing or weakening a negative case
because the implementation fails it is a benchmark regression, not progress.

---

## 12. Initial evaluation priorities

In priority order:

1. **Correct canonical resolution** — right concept for canonical wording.
2. **Correct alias resolution** — abbreviations, common names, market terms.
3. **Ambiguity-state accuracy** — `RESOLVED` / `ASSUMED` / `CLARIFY` correctness.
4. **Clarification precision and recall** — over-asking and under-asking are both defects.
5. **Incorrect expansion rate** — false semantic expansion, measured explicitly. This is
   particularly important: over-expansion is a correctness failure, not a ranking nuisance.
6. **`must_not_infer` violation rate** — must trend to zero.

Results are written to `evaluation-results/`.

---

## 13. Determinism and dependencies

v0.01 is deterministic and dependency-light. No OpenAI, Ollama, Qwen, Transformers,
embeddings, vector databases, or agent frameworks unless a later milestone explicitly
requires them. Standard library, `dataclasses`, `enum`, explicit type annotations, small
single-purpose modules, pure functions where practical, and JSON for the initial ontology
data.

---

## 14. Later milestones

Documented, not implemented.

### v0.02 — semantic / embedding experiment

Compare deterministic lexical resolution against a semantic/embedding approach on the same
benchmark, to establish whether embeddings are actually necessary and at what cost in
false expansion. Depends on v0.01's benchmark being trustworthy.

### Later — Ontology Curator / Terminology Validator

Supporting ongoing ontology quality:

- propose candidate concepts and aliases from observed unknown terminology;
- detect duplicates, near-duplicates and label collisions;
- flag terminology whose maturity has shifted;
- validate relationship search policies;
- surface stale or unused concepts.

**Canonical changes require human review in all cases.** Automated systems propose;
humans dispose. No automatic write to the canonical ontology.

### Candidate terminology sources

No single source defines the complete ontology. Candidate inputs include:

- industry and market terminology sources such as **IT-Harvest**;
- **NIST**;
- **MITRE ATT&CK**;
- **CIS**;
- **OWASP**;
- relevant AI standards and papers;
- academic research;
- vendor documentation;
- wider web terminology;
- aggregated user corrections from the future interface.

---

## 15. Out of scope for v0.01

For the avoidance of doubt, the following are **not** part of this milestone and must not be
created under it: application modules (`models`, `store`, `resolver`, `ambiguity`,
`query_plan`), ontology JSON data files, benchmark data files, tests of behaviour,
LLM/embedding/vector dependencies, Git commits or pushes.