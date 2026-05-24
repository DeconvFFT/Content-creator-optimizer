---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Build a Large Language Model (From Scratch)"
authors: "Sebastian Raschka"
chapter: "6"
chapter_title: "Fine-Tuning for Classification"
source_path: "/Users/saumyamehta/DS interview prep/books/Build a Large Language Model (From Scratch).pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 6 - Fine-Tuning For Classification

## Reading Status

Direct source reading pass completed for chapter 6 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied formulas, copied figures, and long excerpts.

## Core Idea

The chapter adapts a pretrained GPT-style model into a supervised classifier. The workflow is deliberately concrete: prepare a labeled text dataset, balance and split it, tokenize and pad examples, replace the language-model output head with a class head, freeze most pretrained weights, train a small set of task-relevant layers, evaluate with loss and accuracy, and save the resulting classifier.

Agent Studio implication: not every content-moderation, routing, eligibility, or quality decision needs an instruction-following agent. Narrow classification routes can be cheaper, more auditable, and easier to validate when the output space is predefined.

## Classification vs Instruction Fine-Tuning

Classification fine-tuning restricts the model to known labels, while instruction fine-tuning teaches broader task following. The chapter frames classification as the better fit when the product needs precise categorization into fixed classes and instruction fine-tuning as the better fit when the model must handle varied natural-language tasks.

Agent Studio implication: route design should start with output contract, not model fashion. If the decision is `approve/reject`, `spam/not_spam`, `needs_review/no_review`, `source_supported/unsupported`, or `style_match/mismatch`, a classifier route may be the right primitive.

## Dataset Preparation

The chapter uses a labeled spam dataset, then balances classes by undersampling the majority class and splits the data into train, validation, and test sets. The balancing choice makes the example tractable but also shows that class distribution is a modeling decision.

Agent Studio implication:

- store original class distribution before any balancing;
- record balancing, sampling, and split strategy;
- evaluate on a test distribution that matches the production decision surface, not only a convenient balanced sample;
- treat label definitions as schema, not prose.

## Batching And Padding

Messages have variable length, so the dataset class tokenizes each text and pads or truncates examples to a consistent length. Validation and test examples are padded to the training maximum length, with optional truncation when they exceed the training maximum or model context window.

Agent Studio implication: classification pipelines still need tokenizer, padding, truncation, and context policy metadata. A route can silently degrade if production text exceeds the fine-tuning context policy or if padding semantics differ across training and serving.

## Model Modification

The pretrained model initially predicts vocabulary tokens. The classification adaptation replaces the vocabulary-sized output head with a class-sized linear head. Because GPT-style causal attention lets the last token attend to all earlier tokens, the classifier uses the final token representation as the sequence-level decision representation.

Agent Studio implication: sequence classification should document which representation is used for the decision: final token, pooled embedding, special classification token, mean pooling, or external embedding model. That choice affects truncation behavior and interpretability.

## Freezing Strategy

The chapter freezes the pretrained model, then trains the new output head plus the final transformer block and final normalization layer. This is a pragmatic middle ground: cheaper than full fine-tuning, usually stronger than head-only training.

Agent Studio implication: adaptation proposals need an explicit trainable-parameter policy. The datastore should distinguish head-only fine-tune, last-layer fine-tune, full fine-tune, LoRA/adapter fine-tune, and prompt/retrieval-only changes.

## Loss And Accuracy

Classification uses cross entropy over class logits and argmax for label prediction. Accuracy is used for the spam example, first on sampled batches during training and then on the full train/validation/test loaders after training.

Agent Studio implication: accuracy is only enough for balanced, symmetric-cost examples. Production classifiers need task-specific metrics: precision/recall, false-positive cost, false-negative cost, calibration, threshold curves, reviewer override rate, and slice metrics.

## Training And Evaluation Loop

The training loop is close to the pretraining loop: train mode, batch loss, backpropagation, optimizer step, periodic loss checks, and epoch-level accuracy checks. The chapter emphasizes inspecting both training and validation curves to detect overfitting.

Agent Studio implication: classification route promotion should require both optimization evidence and held-out behavior evidence. A route should not ship because training loss went down; it should ship because it improves the production decision under the right cost function.

## Serving The Classifier

The final classifier function reproduces preprocessing at inference time, pads/truncates the new input, runs the model without gradients, reads the last-token logits, and maps the predicted class id to a label.

Agent Studio implication: preprocessing must be part of the deployable artifact. Store tokenizer version, max length, padding token id, truncation strategy, class-id mapping, model checkpoint, and the exact serving wrapper version.

## Datastore Requirements

Agent Studio should store classification adaptation records:

- `classification_dataset`: label schema, class distribution, balancing policy, split ids, sampling seed, source provenance, and allowed use.
- `classification_model_delta`: base model, output head shape, trainable layers, frozen layers, optimizer settings, checkpoint id, and parameter count changed.
- `classification_context_policy`: tokenizer, padding token, max length, truncation side, final-token/pooling strategy, and production overflow handling.
- `classification_eval`: train/validation/test metrics, slice metrics, confusion matrix, threshold policy, calibration result, false-positive/false-negative review examples, and deployment gate decision.
- `classifier_serving_contract`: input normalization, output label map, confidence semantics, fallback route, and human-review escalation rule.

## Failure Modes

- Fine-tuning on a balanced dataset, then deploying into an imbalanced production stream without threshold recalibration.
- Reporting accuracy when false positives and false negatives have different product costs.
- Changing tokenizer or padding behavior between training and serving.
- Using the final-token representation while truncating away the decisive evidence.
- Freezing too much and underfitting, or training too much and overfitting a small labeled dataset.
- Treating a narrow classifier as a general instruction-following model.
- Saving the checkpoint without the label map and preprocessing wrapper.

## Agent Studio Design Implications

- Use classifiers for fixed-label gates inside the agent workflow: source eligibility, moderation, task routing, factual-risk triage, style compliance, and reviewer escalation.
- Make classifier routes first-class `route` records with their own eval gates, not hidden helper scripts.
- Store cost-sensitive metrics and confusion matrices alongside any route that can block, approve, or escalate user-visible content.
- Keep classification fine-tuning separate from instruction fine-tuning in the adaptation decision tree.
- Require preprocessing parity checks before moving a local classifier note or checkpoint into production use.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
