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
  number: 20
  title: "Information Extraction: Relations, Events, and Time"
extraction:
  method: pdftotext
  physical_pages: "444-469"
  temp_extract: "/private/tmp/slp_ch20_ie_relations_events_time.txt"
stores_raw_source_text: false
related:
  - "[[../rag-dialogue-speech-ie]]"
  - "[[../../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../../03-patterns/retrieval/reranking-search-kg-patterns]]"
  - "[[../../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
  - "[[../../../03-patterns/evaluation/retrieval-eval-templates]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 20 - Information Extraction: Relations, Events, And Time

## Reading Scope

This is a direct-read chapter synthesis from the local official/user-provided Speech and Language Processing PDF. It covers Chapter 20 only: relation extraction, pattern systems, supervised relation classification, bootstrapping, distant supervision, Open IE, relation evaluation, event extraction, temporal representation, TimeBank/TimeML, temporal expression extraction and normalization, temporal ordering, and template filling.

This note stores original system-design synthesis only. It does not store copied chapter text, figures, formulas as a reference dump, exercises, or long excerpts.

## Why This Chapter Matters

Agent Studio needs a memory and source graph, but Chapter 20 makes clear that graph facts are not born as facts. They begin as candidate relations, events, temporal expressions, and template slot fills, each with extraction method, evidence span, confidence, and review status.

The design rule: extracted structure can improve retrieval, planning, and publishing only after the datastore preserves:

- the source chunk and entity mentions used as arguments;
- the extraction method and model/rule version;
- whether the relation/event/time/template is closed-schema, Open IE, or domain-specific;
- confidence and calibration evidence;
- temporal anchors and uncertainty;
- merge/coreference decisions;
- whether a human or trusted review path promoted the candidate into source canon.

## Relation Extraction Contracts

Relations can come from fixed ontologies, domain schemas, Wikipedia/DBpedia/Wikidata-style triples, hand-labeled datasets, or open relation phrases. These are different contracts.

Agent Studio should not collapse them into one `edge` table:

| Relation source | Use | Risk |
|---|---|---|
| Hand-built patterns | High-precision extraction for narrow facts such as hypernyms or title/organization patterns. | Low recall and brittle domain coverage. |
| Supervised classifiers | Strong when train/test domains and relation labels match. | Expensive labels and poor genre transfer. |
| Bootstrapping | Expands from seed tuples or seed patterns. | Semantic drift from bad tuples or patterns. |
| Distant supervision | Uses an existing database to create noisy training examples at scale. | Low precision and limited to relations already present in a database. |
| Open IE | Discovers relation phrases without a predefined schema. | Canonicalization and nominal-relation gaps before graph use. |

Agent Studio should store `relation_candidate_record` separately from promoted graph edges. A candidate needs argument refs, relation label or phrase, source span, method, confidence, schema, and review status.

## Pattern, Supervised, And Open IE Implications

Pattern extraction is useful for high-precision source ingestion rules. For example, a known product/source template can extract author, version, dependency, release note, route owner, or benchmark relation with good precision. It should be versioned as `extraction_pattern_record`, not hidden in code.

Supervised relation extraction should declare its label set and negative class. Relation datasets often contain many "no relation" examples, so precision/recall must be interpreted with class imbalance and route value in mind.

Open IE is valuable for exploratory graph building because it can discover relation strings without a schema. It should feed a review and canonicalization lane, not directly mutate ontology-level facts. Agent Studio should keep `openie_triple_record` with raw relation phrase hash, normalized phrase, argument refs, confidence, and canonicalization status.

## Bootstrapping And Distant Supervision

Bootstrapping creates a feedback loop: tuples create patterns, patterns create more tuples. That is useful, but it is also how semantic drift enters the graph. Agent Studio should log `bootstrapping_iteration_record` with seed tuples/patterns, newly accepted candidates, confidence thresholds, rejected examples, and drift audit samples.

Distant supervision is a data-generation strategy, not a truth guarantee. It assumes a database relation can label sentences containing the entity pair, but a sentence may mention both entities without expressing the relation. Agent Studio should store `distant_supervision_bag_record` with database source, entity pair, relation label, sentence refs, noise assumptions, and negative-sampling policy.

Promotion policy:

- candidates from bootstrapping or distant supervision can improve recall;
- they cannot become canonical graph facts without confidence checks, source evidence, and review or high-precision policy;
- low-confidence candidates are still useful as retrieval hints or eval cases.

## Relation Evaluation

Closed-schema relation extraction can use gold test sets with precision, recall, and F-measure. Semi-supervised and Open IE systems often cannot measure recall directly at web scale, so sampled precision and precision-at-yield become more realistic.

Agent Studio should store `relation_eval_sample_record` for extraction routes:

- relation family or schema;
- candidate population;
- random sample policy;
- reviewer decision protocol;
- precision estimate;
- confidence/yield curve;
- known blind spots such as nominal relations, rare entity types, or domain shift.

## Events And Temporal Graphs

Events are not just verbs. They can be introduced by nouns, reporting verbs, light-verb constructions, states, activities, accomplishments, and achievements. This matters because Agent Studio source memory often needs to know what happened, what merely held true, what was reported, and what was planned.

Minimum event records:

| Object | Purpose |
|---|---|
| `event_mention_record` | Event or state mention with trigger span, event class, tense, aspect, modality, and source evidence. |
| `event_argument_record` | Participant, role, source mention, and confidence for an event. |
| `event_aspect_record` | Aspectual class and temporal contour such as state, activity, accomplishment, or achievement. |
| `temporal_link_record` | Event-event, event-time, time-time, document-time, aspectual, or factuality link. |

For Agent Studio, this prevents unsafe timeline claims. A source saying a company "expects to obtain approval" is not the same as the approval occurring.

## Temporal Normalization And Anchors

Temporal expressions include absolute dates, relative expressions, durations, recurring sets, and vague phrases. Normalization often depends on a document creation time or another anchor event. Rules like "last week", "the weekend", or "two weeks after" require anchor policy and temporal arithmetic.

Agent Studio should extend `temporal_expression_record` with:

- expression type: absolute, relative, duration, set, vague;
- normalized value or interval;
- document creation time or event anchor;
- timezone and locale assumptions;
- ambiguity and candidate alternatives;
- normalization rule/model version.

The release rule: a route should not schedule, publish, expire, refresh, or order source facts using normalized time unless the anchor and uncertainty are preserved.

## Template Filling

Template filling connects relations and events into stereotyped situations with slots. This is useful for Agent Studio workflows such as ingestion incident reports, provider outages, benchmark result reports, release notes, user feedback incidents, and content-publication approvals.

Template filling is also where inference can silently enter the datastore. A slot filler can be directly extracted or inferred from context. The datastore should record the difference.

Required records:

| Object | Purpose |
|---|---|
| `template_schema_record` | Versioned event/script template with required and optional slots. |
| `template_candidate_record` | Detected template instance before promotion. |
| `template_slot_fill_record` | Extracted or inferred slot filler, evidence, confidence, and role. |
| `template_merge_record` | Merge of partial templates after coreference/entity/event resolution. |

For Agent Studio, a filled template should become a reviewed structured artifact, not an invisible side effect of a summarizer.

## Agent Studio Design Implications

- Keep relation, event, time, and template candidates separate from promoted graph facts.
- Version extraction patterns, classifier label sets, Open IE phrase normalization, and bootstrapping thresholds.
- Treat bootstrapping and distant supervision as recall tools with drift/noise audits, not as authority.
- Store sampled precision and precision-at-yield for large-scale extraction routes.
- Preserve tense, aspect, modality, reporting status, and factuality before using events as memory.
- Require document-time, event-time, timezone, and ambiguity records before using temporal claims for scheduling or freshness.
- Use template filling for repeated operational stories, but record extracted versus inferred slot values and merge decisions.
- Connect IE output to retrieval as evidence candidates first; promote to source graph only after review, confidence, and provenance gates.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-whole-part-hierarchies]] - Stanford CS25, "Whole-Part Hierarchies in a Neural Network" ([YouTube](https://www.youtube.com/watch?v=CYaju6aCMoQ)).
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
