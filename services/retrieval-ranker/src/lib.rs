pub mod contracts;
pub mod graph;
pub mod scorer;
pub mod service;

pub use contracts::{
    Candidate, CandidateSignals, GraphEdge, GraphTraversalRequest, GraphTraversalResponse,
    RankRequest, RankResponse, RetrievalRankerRequest, RetrievalRankerResponse, ScoringConfig,
};
pub use graph::traverse_graph;
pub use scorer::rank_candidates;
pub use service::handle_request;
