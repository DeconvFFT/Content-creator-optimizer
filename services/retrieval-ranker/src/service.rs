use crate::contracts::{RetrievalRankerRequest, RetrievalRankerResponse};
use crate::graph::traverse_graph;
use crate::scorer::rank_candidates;

pub fn handle_request(request: RetrievalRankerRequest) -> RetrievalRankerResponse {
    match request {
        RetrievalRankerRequest::Rank(rank_request) => {
            RetrievalRankerResponse::Rank(rank_candidates(rank_request))
        }
        RetrievalRankerRequest::TraverseGraph(graph_request) => {
            RetrievalRankerResponse::TraverseGraph(traverse_graph(graph_request))
        }
    }
}
