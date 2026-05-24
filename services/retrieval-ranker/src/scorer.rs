use crate::contracts::{
    Candidate, CandidateSignals, RankDiagnostics, RankRequest, RankResponse, RankedCandidate,
    ScoreBreakdown, ScoringConfig,
};
use std::collections::BTreeSet;

const SCORING_VERSION: &str = "deterministic_linear_v1";

pub fn rank_candidates(request: RankRequest) -> RankResponse {
    let config = sanitize_config(request.config);
    let query_terms = tokenize(&request.query);
    let candidate_count = request.candidates.len();

    let mut results: Vec<RankedCandidate> = request
        .candidates
        .into_iter()
        .map(|candidate| score_candidate(candidate, &query_terms, config))
        .collect();

    results.sort_by(|left, right| {
        right
            .score
            .total_cmp(&left.score)
            .then_with(|| left.id.cmp(&right.id))
    });

    results.truncate(config.limit);
    for (index, result) in results.iter_mut().enumerate() {
        result.rank = index + 1;
    }

    let returned_count = results.len();
    RankResponse {
        request_id: request.request_id,
        results,
        diagnostics: RankDiagnostics {
            candidate_count,
            returned_count,
            scoring_version: SCORING_VERSION.to_string(),
        },
    }
}

fn score_candidate(
    candidate: Candidate,
    query_terms: &BTreeSet<String>,
    config: ScoringConfig,
) -> RankedCandidate {
    let signals = candidate.signals;
    let lexical_component = signals
        .lexical_score
        .map(clamp_unit)
        .unwrap_or_else(|| lexical_overlap(query_terms, &candidate));

    let explanation = ScoreBreakdown {
        vector_component: signals.vector_score.map(clamp_unit).unwrap_or(0.0),
        lexical_component,
        graph_component: graph_component(signals),
        authority_component: signals.authority.map(clamp_unit).unwrap_or(0.0),
        freshness_component: freshness_component(signals),
    };

    let score = weighted_score(explanation, config);

    RankedCandidate {
        id: candidate.id,
        rank: 0,
        score: round_score(score),
        source_uri: candidate.source_uri,
        metadata: candidate.metadata,
        explanation,
    }
}

fn sanitize_config(config: ScoringConfig) -> ScoringConfig {
    ScoringConfig {
        vector_weight: non_negative(config.vector_weight),
        lexical_weight: non_negative(config.lexical_weight),
        graph_weight: non_negative(config.graph_weight),
        authority_weight: non_negative(config.authority_weight),
        freshness_weight: non_negative(config.freshness_weight),
        limit: config.limit.max(1),
    }
}

fn weighted_score(explanation: ScoreBreakdown, config: ScoringConfig) -> f64 {
    let weighted_sum = explanation.vector_component * config.vector_weight
        + explanation.lexical_component * config.lexical_weight
        + explanation.graph_component * config.graph_weight
        + explanation.authority_component * config.authority_weight
        + explanation.freshness_component * config.freshness_weight;
    let weight_sum = config.vector_weight
        + config.lexical_weight
        + config.graph_weight
        + config.authority_weight
        + config.freshness_weight;

    if weight_sum == 0.0 {
        0.0
    } else {
        weighted_sum / weight_sum
    }
}

fn graph_component(signals: CandidateSignals) -> f64 {
    signals
        .graph_distance
        .map(|distance| 1.0 / (1.0 + f64::from(distance)))
        .unwrap_or(0.0)
}

fn freshness_component(signals: CandidateSignals) -> f64 {
    signals
        .freshness_days
        .map(|days| 1.0 / (1.0 + f64::from(days) / 30.0))
        .unwrap_or(0.0)
}

fn lexical_overlap(query_terms: &BTreeSet<String>, candidate: &Candidate) -> f64 {
    if query_terms.is_empty() {
        return 0.0;
    }

    let haystack = match &candidate.title {
        Some(title) => format!("{} {}", title, candidate.text),
        None => candidate.text.clone(),
    };
    let candidate_terms = tokenize(&haystack);
    let hits = query_terms
        .iter()
        .filter(|term| candidate_terms.contains(*term))
        .count();

    hits as f64 / query_terms.len() as f64
}

fn tokenize(value: &str) -> BTreeSet<String> {
    value
        .split(|character: char| !character.is_ascii_alphanumeric())
        .filter_map(|token| {
            let normalized = token.trim().to_ascii_lowercase();
            if normalized.is_empty() {
                None
            } else {
                Some(normalized)
            }
        })
        .collect()
}

fn clamp_unit(value: f64) -> f64 {
    if value.is_nan() {
        0.0
    } else {
        value.clamp(0.0, 1.0)
    }
}

fn non_negative(value: f64) -> f64 {
    if value.is_nan() {
        0.0
    } else {
        value.max(0.0)
    }
}

fn round_score(value: f64) -> f64 {
    (value * 1_000_000.0).round() / 1_000_000.0
}
