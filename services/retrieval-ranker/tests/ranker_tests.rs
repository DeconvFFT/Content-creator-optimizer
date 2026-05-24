use pretty_assertions::assert_eq;
use retrieval_ranker::{
    handle_request, rank_candidates, traverse_graph, Candidate, CandidateSignals, GraphEdge,
    GraphTraversalRequest, RankRequest, RetrievalRankerRequest, RetrievalRankerResponse,
    ScoringConfig,
};

fn candidate(id: &str, text: &str, vector_score: f64) -> Candidate {
    Candidate {
        id: id.to_string(),
        text: text.to_string(),
        title: None,
        source_uri: None,
        metadata: Default::default(),
        signals: CandidateSignals {
            vector_score: Some(vector_score),
            lexical_score: None,
            graph_distance: None,
            authority: None,
            freshness_days: None,
        },
    }
}

#[test]
fn ranks_candidates_by_weighted_score() {
    let response = rank_candidates(RankRequest {
        request_id: Some("rank-1".to_string()),
        query: "retrieval graph evidence".to_string(),
        candidates: vec![
            candidate("low-vector-strong-lexical", "retrieval graph evidence", 0.2),
            candidate("high-vector-weak-lexical", "unrelated draft", 0.9),
        ],
        config: ScoringConfig {
            vector_weight: 0.4,
            lexical_weight: 0.6,
            graph_weight: 0.0,
            authority_weight: 0.0,
            freshness_weight: 0.0,
            limit: 10,
        },
    });

    assert_eq!(response.results[0].id, "low-vector-strong-lexical");
    assert_eq!(response.results[0].rank, 1);
    assert_eq!(response.results[1].rank, 2);
    assert_eq!(response.diagnostics.candidate_count, 2);
}

#[test]
fn breaks_score_ties_by_candidate_id() {
    let response = rank_candidates(RankRequest {
        request_id: None,
        query: "same".to_string(),
        candidates: vec![candidate("b", "same", 0.5), candidate("a", "same", 0.5)],
        config: ScoringConfig {
            vector_weight: 1.0,
            lexical_weight: 0.0,
            graph_weight: 0.0,
            authority_weight: 0.0,
            freshness_weight: 0.0,
            limit: 10,
        },
    });

    let ids: Vec<&str> = response
        .results
        .iter()
        .map(|candidate| candidate.id.as_str())
        .collect();
    assert_eq!(ids, vec!["a", "b"]);
}

#[test]
fn traverses_graph_breadth_first_with_stable_order() {
    let response = traverse_graph(GraphTraversalRequest {
        request_id: Some("graph-1".to_string()),
        start_node_id: "root".to_string(),
        max_depth: 2,
        limit: 10,
        edges: vec![
            GraphEdge {
                from: "root".to_string(),
                to: "z".to_string(),
                relation: "mentions".to_string(),
            },
            GraphEdge {
                from: "root".to_string(),
                to: "a".to_string(),
                relation: "supports".to_string(),
            },
            GraphEdge {
                from: "a".to_string(),
                to: "leaf".to_string(),
                relation: "contains".to_string(),
            },
        ],
    });

    let ids: Vec<&str> = response
        .visited
        .iter()
        .map(|node| node.node_id.as_str())
        .collect();
    assert_eq!(ids, vec!["root", "a", "z", "leaf"]);
    assert_eq!(response.visited[3].depth, 2);
    assert_eq!(response.visited[3].parent_node_id.as_deref(), Some("a"));
}

#[test]
fn dispatches_typed_requests() {
    let response = handle_request(RetrievalRankerRequest::Rank(RankRequest {
        request_id: Some("dispatch-1".to_string()),
        query: "source".to_string(),
        candidates: vec![candidate("source-1", "source evidence", 0.3)],
        config: ScoringConfig::default(),
    }));

    match response {
        RetrievalRankerResponse::Rank(rank_response) => {
            assert_eq!(rank_response.request_id.as_deref(), Some("dispatch-1"));
            assert_eq!(rank_response.results[0].id, "source-1");
        }
        RetrievalRankerResponse::TraverseGraph(_) => panic!("expected rank response"),
    }
}
