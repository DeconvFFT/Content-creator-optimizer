---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_or_open_public
provenance_status: official_document_ai_textract_azure_docling_unstructured_docs_direct_read
sources:
  - https://docs.cloud.google.com/document-ai/docs/layout-parse-chunk
  - https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr#ocr-processing
  - https://docs.aws.amazon.com/textract/latest/dg/API_AnalyzeDocument.html
  - https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout?view=doc-intel-3.0.0&viewFallbackFrom=form-recog-3.0.0
  - https://docling-project.github.io/docling/
  - https://docling-project.github.io/docling/usage/supported_formats/
  - https://docs.unstructured.io/open-source/introduction/overview
  - https://docs.unstructured.io/open-source/introduction/supported-file-types
  - https://docs.unstructured.io/open-source/core-functionality/partitioning
---

# Document Layout And OCR Ingestion Runtime

## Scope

Direct-read synthesis from official Google Document AI layout parser and Enterprise OCR docs, Amazon Textract AnalyzeDocument docs, Azure AI Document Intelligence layout docs, Docling docs, and Unstructured open-source docs. This note covers Agent Studio ingestion for PDFs, JPEG/JPG images, DOC/DOCX, and other structured documents. It stores no raw OCR output, document text, code samples, or long excerpts.

## Core Pattern

Document ingestion is a lossy model/runtime pipeline, not a file read. A PDF, image, or DOCX can produce text, tables, figures, headings, checkboxes, forms, page geometry, reading order, OCR confidence, language hints, quality scores, and layout-aware chunks. Different parsers return different element types and failure modes, so the datastore must preserve parser choice and extraction evidence.

Agent Studio should treat every source-document pass as a governed conversion:

- identify file type and allowed-use status;
- choose parser strategy by format, scan quality, table/layout complexity, privacy boundary, cost, and latency;
- preserve page coverage, parser version, processor/model version, and configuration;
- store element-level structure and confidence where available;
- record known losses for tables, figures, formulas, handwriting, nested tables, multi-page tables, hidden content, and reading order;
- gate downstream retrieval or note synthesis on extraction quality, not just extraction success.

## Cross-Provider Design Signals

Google Document AI separates OCR from Gemini layout parsing. Enterprise Document OCR extracts text and layout information from documents and exposes options such as page ranges, language or handwriting hints, rotation correction, image quality scoring, and model version pinning. Gemini layout parser targets RAG and discovery workflows by preserving structure, hierarchy, tables, figures, and context-aware chunks, with different limits for online and batch processing.

Amazon Textract AnalyzeDocument returns structured block relationships for text, tables, forms, queries, signatures, selection elements, and layout. The API shape makes a key point for Agent Studio: extracted elements are graph-like records with relationships and confidence, not a flat text stream. Synchronous and asynchronous processing should be modeled separately.

Azure Document Intelligence layout combines OCR with layout models to extract text, tables, selection marks, and document structure. It also exposes format and size constraints, including Office document behavior. This reinforces that DOCX/PPTX-style sources need a different policy from scanned PDFs and images.

Docling and Unstructured are useful local/open conversion lanes. Docling converts many file formats into a unified document representation and can export structured formats including Markdown, JSON, text, and DocTags. Unstructured partitions raw documents into typed elements and routes files to format-specific partition functions, including PDF/image strategies and Word document parsers. These are not replacements for extraction QA; they are parser runtimes with their own strategy and dependency records.

## Current-Source Cross-Check

Current Google Document AI layout-parser guidance reinforces that document ingestion for RAG is a structured layout pipeline, not plain OCR. Its current parser versions, file-type limits, table/figure handling, layout-aware chunking, page limits, and data-residency caveats support treating parser version, format support, chunking policy, and provider boundary as release evidence.

Current AWS Textract AnalyzeDocument guidance reinforces the graph-record model: blocks carry page, geometry, confidence, relationships, selection state, row and column spans, document metadata, and model version. Agent Studio should preserve those relationships rather than flatten them into source text before QA.

Current Azure Document Intelligence layout guidance supports the same contract for a different managed provider: layout extraction covers pages, paragraphs, text, lines, words, selection marks, tables, natural reading order, page ranges, bounding regions, confidence, and supported file constraints.

Current Docling and Unstructured docs support local/open parser lanes, but also show why local parsing still needs explicit strategy records. Format support, image/PDF strategy, OCR fallback, layout classification, table extraction, dependency availability, and copy-protected or multi-column behavior can change extraction quality and downstream retrieval trust.

## Agent Studio Design Implications

- Store parser output as structured artifacts, not as raw copied text inside Obsidian notes.
- Use local/open parsers first when privacy, cost, or offline operation matters; use managed Document AI/Textract/Azure lanes when layout quality, OCR quality, or scale justifies provider exposure.
- Keep page-level and element-level records so retrieval can cite page, heading, table, figure, and bounding-box context.
- Treat layout-aware chunking as a release choice. It can improve RAG quality, but it can also hide split tables, omitted figures, or bad reading order if not measured.
- Record parser limits per file type. DOCX, scanned PDF, born-digital PDF, image, and table-heavy report are not equivalent sources.
- OCR confidence, image-quality score, language hints, and rotation correction should influence whether a source is accepted, reprocessed, or sent to human review.
- Table extraction needs separate QA. Tables can be split, misaligned, flattened, or hallucinated by model-heavy parsers.
- Page range selection is a cost and correctness control. A partial-page extraction must not masquerade as full-document coverage.
- Downstream note synthesis should cite extraction artifact IDs and coverage status, never only the original filename.

## Datastore Additions

| Object | Purpose | Key fields |
|---|---|---|
| `document_parser_profile` | Parser/runtime capability and boundary record | `parser_profile_id`, `provider_or_library`, `parser_name`, `version_or_processor_ref`, `supported_formats`, `supported_elements`, `sync_async_modes`, `privacy_boundary`, `cost_latency_class`, `known_limits`, `status` |
| `document_extraction_job` | One extraction run over a local or remote source artifact | `extraction_job_id`, `source_id`, `input_artifact_id`, `parser_profile_id`, `strategy`, `page_range_policy`, `ocr_language_hints`, `quality_options`, `started_at`, `finished_at`, `status`, `error_summary` |
| `document_page_coverage` | Proof of which pages/images/slides were processed | `coverage_id`, `extraction_job_id`, `page_count_detected`, `pages_requested`, `pages_processed`, `pages_skipped`, `partial_extraction_reason`, `coverage_decision`, `created_at` |
| `document_layout_element` | Structured extracted element before chunking | `element_id`, `extraction_job_id`, `page_ref`, `element_type`, `parent_element_id`, `heading_path_ref`, `bbox_or_region_ref`, `text_hash`, `confidence`, `reading_order`, `metadata_refs` |
| `table_extraction_record` | Table-specific structure and quality evidence | `table_record_id`, `element_id`, `page_refs`, `row_count`, `column_count`, `header_refs`, `merged_cell_flags`, `multi_page_split_flag`, `html_or_structured_ref`, `quality_flags`, `review_status` |
| `document_quality_signal` | OCR/layout quality and routing evidence | `quality_signal_id`, `extraction_job_id`, `page_ref`, `signal_type`, `metric_value`, `threshold`, `risk_flag`, `recommended_action`, `created_at` |
| `layout_chunk_record` | Layout-aware chunk produced from extracted elements | `layout_chunk_id`, `extraction_job_id`, `source_chunk_id`, `element_refs`, `ancestral_heading_refs`, `table_or_figure_refs`, `token_count`, `chunking_policy_id`, `retrieval_ready_status` |
| `extraction_fallback_decision` | Parser retry or escalation decision | `fallback_id`, `extraction_job_id`, `failure_or_risk_signal`, `candidate_parser_profiles`, `selected_next_parser`, `human_review_required`, `cost_privacy_tradeoff`, `decision`, `created_at` |
| `document_ingestion_release_gate` | Promotion gate for document-derived retrieval, eval, or canon evidence | `gate_id`, `source_id`, `candidate_extraction_job_id`, `parser_profile_refs`, `page_coverage_ref`, `layout_element_refs`, `table_quality_refs`, `document_quality_signal_refs`, `layout_chunk_policy_ref`, `fallback_decision_refs`, `privacy_provider_boundary_refs`, `known_loss_summary`, `decision`, `reviewed_at` |

## Release Gates

Do not allow a document source to become retrieval or canon evidence when:

- file provenance or allowed use is unknown;
- extraction job lacks parser/version/config metadata;
- processed page coverage is unknown or partial without an explicit caveat;
- OCR/layout quality is below the route threshold;
- table/figure/form extraction is required but no element-level QA exists;
- born-digital and scanned PDFs are handled by the same unreviewed strategy;
- DOC/DOCX or Office parsing limits are ignored;
- provider exposure violates privacy or retention policy;
- downstream chunks lack page, heading, and element lineage.

## Agent Studio Decision

This note is canon-ready for Agent Studio ingestion architecture. Use document parsing as a first-class ingestion runtime. The data store should make source file, parser profile, extraction job, page coverage, layout elements, tables, quality signals, layout-aware chunks, fallback decisions, and document-ingestion release gates queryable before any PDF/JPEG/DOC/DOCX source can support retrieval, evals, or Agent Studio design notes.
