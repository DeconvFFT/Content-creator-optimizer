---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-20
cross_checks:
  - source_title: "Python NLP Cookbook Chapter 2"
    scope: "Dependency parsing, subject/object extraction, noun-chunk boundaries, and declarative matcher patterns"
anchor_note: "02-books/python-nlp-cookbook/chapters/ch02-dependency-subject-object-extraction.md"
sources:
  - https://spacy.io/usage/linguistic-features
  - https://spacy.io/api/doc
  - https://spacy.io/api/token
  - https://spacy.io/usage/rule-based-matching
  - https://spacy.io/api/matcher
  - https://spacy.io/api/dependencymatcher
  - https://universaldependencies.org/u/dep/
  - https://universaldependencies.org/u/dep/all.html
related:
  - "[[../../02-books/python-nlp-cookbook/chapters/ch02-dependency-subject-object-extraction]]"
  - "[[../../02-books/python-nlp-cookbook/source-ingestion-nlp-recipes]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Python NLP Cookbook Chapter 2 - Dependency Extraction Cross-Check

## Scope

This cross-check sharpens the cookbook's Chapter 2 grammar slice with current official spaCy documentation plus Universal Dependencies definitions. The goal is not to replace the book note, but to harden its implementation meaning: what exactly parser labels mean, what `Doc`/`Token`/`Matcher` expose, and where dependency rules stop being trustworthy.

## Cross-Check Result

The chapter note is directionally correct and production-relevant. The official docs strengthen it in four ways:

1. they make the parse-tree APIs explicit rather than cookbook-implicit;
2. they separate token-sequence matching from dependency-tree matching;
3. they clarify that noun chunks and dependency labels depend on parser/language support;
4. they align subject/object logic with Universal Dependencies rather than ad hoc intuition.

## Confirmation Matrix

| Cookbook theme | Official/open confirmation | Agent Studio implication |
|---|---|---|
| Dependency parse as structural evidence | spaCy exposes parse structure directly on `Token` and `Doc` through dependency labels, heads, children, ancestors, subtrees, and noun-chunk iteration. | Treat the parse as a first-class intermediate artifact; candidate extractors should reference parse outputs explicitly instead of burying them in custom helper code. |
| Subject/object extraction should use dependency families | UD definitions make relations like subject and object semantic enough to be portable, while spaCy supplies the concrete labels on tokens. | Document extractor rules in UD-aligned language so grammar candidates remain interpretable across model revisions and future runtime swaps. |
| Noun chunks are parser-backed phrase candidates | `Doc.noun_chunks` is not a string heuristic; it depends on parse support and yields base noun phrases. | Use noun chunks as bounded candidate spans, but gate them behind parser/language availability checks. |
| Token-subtree span recovery preserves evidence | `Token.subtree` and span indexing justify returning full phrase spans rather than only head tokens. | Store both head token and subtree span so retrieval, citation, and canonicalization can choose the right granularity. |
| Matcher patterns are declarative token rules | spaCy `Matcher` works on token attributes such as `POS`, `LEMMA`, `DEP`, flags, and quantifiers. | Keep pattern rules as versioned declarative data rather than ad hoc imperative conditionals. |
| DependencyMatcher is the structural escalation path | spaCy officially distinguishes sequence matching from dependency-tree matching. | Use `Matcher` for local token-shape rules; escalate to `DependencyMatcher` when the rule depends on parse topology. |
| Grammar is candidate generation, not truth | Neither UD nor spaCy makes parse labels equivalent to factual relation extraction. | Route grammar outputs into review, retrieval, and entity-linking stages before canon promotion. |

## Hardening Points The Book Note Should Keep Explicit

- Parser output is model-dependent; deterministic rules still inherit statistical parser error.
- Subject extraction must not be overclaimed as actor extraction when passive or reporting constructions are present.
- Prepositional objects are often many-valued and should remain a list, not a single slot.
- Matcher outputs can contain partial overlaps; post-filtering is part of the runtime contract.
- Dependency-tree extraction requires parse support; it is not safe to assume every language/model bundle exposes identical behavior.

## Agent Studio Design Rules Confirmed

1. **Dependency labels are adapter inputs, not hidden implementation details.** Extraction records should persist parser label family and parser version.
2. **Head token and recovered phrase span should both be stored.** They solve different downstream problems.
3. **Matcher and DependencyMatcher should be treated as separate route classes.** Linear token rules and tree-structural rules are not interchangeable.
4. **UD-aligned naming improves portability.** Keep design docs framed around standard relation families instead of model-specific folklore.
5. **Grammar-derived outputs stay in the candidate lane until corroborated.** Retrieval, entity linking, or human review should decide canon promotion.

## Bottom Line

The official/open sources confirm the cookbook chapter as a valid low-cost grammar-extraction foundation, but they also sharpen the boundary:

> dependency parsing, noun chunks, and matcher rules are best treated as reproducible candidate-generators whose value depends on parser support, version pinning, and downstream verification.
