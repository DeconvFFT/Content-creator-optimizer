---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source:
  local_path: /Users/saumyamehta/DS interview prep/books/NLPbook.pdf
  title: "Speech and Language Processing"
  authors: "Daniel Jurafsky and James H. Martin"
  edition: "Third Edition draft, January 12, 2025"
chapter:
  number: 23
  title: "Coreference Resolution and Entity Linking"
extraction:
  method: pdftotext
  physical_pages: "509-538"
  temp_extract: "/private/tmp/slp_ch23_coreference_entity_linking.txt"
stores_raw_source_text: false
related:
  - "[[../rag-dialogue-speech-ie]]"
  - "[[../../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 23 - Coreference Resolution And Entity Linking

## Reading Scope

This is a direct-read chapter synthesis from the local official/user-provided Speech and Language Processing PDF. It covers Chapter 23 only: mentions, discourse entities, anaphora, mention detection, coreference datasets and architectures, neural span-ranking coreference, entity linking, coreference evaluation, Winograd-style reasoning, and gender-bias evaluation.

This note stores original system-design synthesis only. It does not store copied chapter text, figures, formulas as a reference dump, exercises, or long excerpts.

## Why This Chapter Matters

Agent Studio cannot safely build memory or a source graph by treating every noun phrase as a fact and every entity-looking string as a canonical entity. Chapter 23 makes the missing layer explicit:

- a `mention` is a source span;
- a `discourse entity` is what a cluster of mentions refers to inside one discourse;
- a `coreference chain` is the system's proposed cluster of mentions for that discourse entity;
- an `entity link` maps a mention or chain to a real-world ontology or knowledge-base target.

The design rule: source graph writes must keep mention detection, coreference clustering, and entity linking as separate, reviewable stages. Collapsing them into one "entity id" hides the exact place where many memory errors enter.

## Mention And Discourse Model Contracts

Coreference starts with a discourse model, not a global database. A document may introduce entities, revisit them through pronouns or descriptions, nest one mention inside another, or describe something that looks like a noun phrase but is not a referential mention.

Agent Studio should store `mention_record` with:

| Field group | Reason |
|---|---|
| source span and offsets | Needed to audit exactly what text grounded the mention. |
| mention type | Name, definite NP, indefinite NP, pronoun, zero pronoun if applicable, demonstrative, or nested mention. |
| referentiality/anaphoricity status | Needed because expletives, generics, predicate nominals, appositives, and non-referring NPs should not become graph entities. |
| information status | New, old, inferable, bridged, or unknown; useful for dialogue and document memory. |
| review status | Important before using the mention in graph facts or user-visible claims. |

The high-risk case is over-generous mention detection. Modern systems often propose many candidate spans and filter later; that is good for recall but dangerous if the datastore treats candidate mentions as accepted entities.

## Coreference Architecture Implications

Chapter 23 separates three common architecture families:

| Architecture | Useful mental model | Product risk |
|---|---|---|
| Mention-pair | Binary classifier over candidate anaphor and antecedent pairs. | Simple but locally myopic; transitive closure can spread pairwise mistakes into bad clusters. |
| Mention-rank | Scores all prior candidate antecedents, including a dummy/no-antecedent option. | Better comparison among antecedents, but still needs careful handling of discourse-new and non-anaphoric mentions. |
| Entity-based | Links a mention to an existing cluster/discourse entity. | More expressive, but cluster state can amplify early merge errors. |

Agent Studio should preserve a `coreference_merge_decision_record`, not only the final cluster. A useful record contains candidate mention, candidate antecedent or cluster, model/rule version, scores, dummy/no-link decision, accepted merge, rejected alternatives, and rollback/review status.

For neural span-ranking systems, the practical datastore lesson is that mention score and antecedent score are different signals. The route should preserve both:

- mention score: is this span likely to be a real mention?
- antecedent score: if it is a mention, which prior mention or cluster should it link to?
- dummy/no-antecedent decision: did the model decide this starts a new chain or is not an anaphor?

## Dataset And Evaluation Caveats

Coreference scores are not portable unless the dataset contract is known. Some datasets omit singletons; some provide gold mentions; some require systems to detect mentions from raw text; some annotate bridging, discourse deixis, generics, or richer information status.

Agent Studio should not use a single "coref F1" as a release gate. `coreference_eval_record` should identify:

- dataset and genre;
- whether singletons are annotated;
- whether mention boundaries are gold or predicted;
- language and domain;
- metric protocol: MUC, B3, CEAF, BLANC, LEA, CoNLL average, NEC-style named-entity-chain metric, or task-specific metric;
- known metric bias, such as MUC favoring larger chains and ignoring singletons;
- whether the route is evaluated on the same surface where it will be used.

For source graph construction, a chain with correct pronouns but no correct named entity can be operationally useless. Evaluation should include task-specific checks for named entity anchoring, alias resolution, and graph-write correctness.

## Entity Linking Contracts

Entity linking is a separate step from coreference. A coreference chain answers "which mentions in this discourse refer to the same discourse entity?" Entity linking answers "which real-world entity, ontology node, or KB id should this discourse entity map to?"

Agent Studio should store `entity_candidate_record` and `entity_link_record` separately:

| Record | Purpose |
|---|---|
| `entity_candidate_record` | Candidate KB/ontology targets for a mention or chain, with generator, prior, coherence, embedding score, and source of the candidate set. |
| `entity_link_record` | Selected target, ontology/version, candidate set refs, model/rule route, confidence, NIL/unlinkable policy, and review status. |
| `nil_entity_record` | Explicit evidence that no existing ontology target should be linked. |
| `entity_canonicalization_record` | Alias, redirect, merge, ontology-version, and de-duplication decisions before graph promotion. |

Anchor-dictionary and graph-coherence linkers are strong baselines because they expose useful product signals: prior probability from anchor usage, link probability, and coherence with other linked entities in the same text. Neural bi-encoder linkers add scalable candidate scoring by encoding mention spans and entity descriptions separately, but they still need candidate provenance, ontology version, and NIL handling.

## Reasoning And Bias

Winograd-style examples show that some coreference decisions require world knowledge, discourse explanation, or commonsense reasoning. A large language model may answer many of these cases, but Agent Studio should treat them as hard ambiguity signals, not silent graph writes.

Bias is a release issue. Coreference systems can perform worse on anti-stereotypical gender examples and on feminine pronoun resolution, partly due to dataset imbalance and representation bias. Agent Studio should add `coreference_bias_eval_slice` for:

- gendered pronouns and occupations;
- names and demographic proxies;
- languages with zero pronouns or grammatical gender;
- dialogue or speech transcripts where ASR errors alter pronouns/names;
- domain-specific roles such as authors, reviewers, creators, clients, and organizations.

Bias mitigation should be tied to evaluation evidence, not assumed from the base model. Data augmentation, balanced datasets, debiased representations, or human review can help only if the route records before/after behavior on the relevant slices.

## Agent Studio Design Implications

- Do not turn detected mentions directly into graph entities.
- Preserve mention spans, nested mentions, referentiality, and information status before clustering.
- Store coreference merge decisions and rejected alternatives so bad clusters can be audited and rolled back.
- Keep discourse-entity chains separate from real-world entity links.
- Require entity candidate sets, ontology version, NIL policy, and canonicalization evidence before graph writes.
- Treat coreference and linking outputs as graph candidates until reviewed or covered by a high-precision release gate.
- Evaluate coreference on the same task surface used by Agent Studio: source summarization, graph writes, claim support, dialogue memory, or retrieval expansion.
- Add bias and hard-reasoning slices before using pronoun/name resolution to personalize, attribute claims, merge users, merge organizations, or publish source-backed content.

## Datastore Objects Promoted By This Chapter

| Object | Role |
|---|---|
| `mention_record` | Source span candidate or accepted mention with type, offsets, nested refs, and referentiality status. |
| `mention_detection_candidate_record` | High-recall span proposal before filtering or acceptance. |
| `referentiality_decision_record` | Decision that a span is referential, non-referential, generic, expletive, appositive, predicate, or uncertain. |
| `coreference_merge_decision_record` | Scored merge/no-merge decision between a mention and a prior mention or chain. |
| `coreference_chain_record` | Accepted cluster of mentions representing a discourse entity. |
| `coreference_eval_record` | Dataset, metric, genre, singleton/gold-mention policy, task caveats, and score summary. |
| `entity_candidate_record` | Candidate ontology/KB targets with prior, coherence, embedding, or search scores. |
| `entity_link_record` | Selected entity target and review status for a mention or coreference chain. |
| `nil_entity_record` | Explicit unlinkable/new-entity decision. |
| `entity_canonicalization_record` | Alias, redirect, merge, and ontology-version decision. |
| `coreference_bias_eval_slice` | Bias and hard-reasoning slice result for the route. |

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
