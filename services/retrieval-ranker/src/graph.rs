use crate::contracts::{GraphEdge, GraphTraversalRequest, GraphTraversalResponse, VisitedNode};
use std::collections::{BTreeMap, BTreeSet, VecDeque};

pub fn traverse_graph(request: GraphTraversalRequest) -> GraphTraversalResponse {
    let adjacency = build_adjacency(&request.edges);
    let limit = request.limit.max(1);
    let mut visited_ids = BTreeSet::new();
    let mut visited = Vec::new();
    let mut queue = VecDeque::new();

    visited_ids.insert(request.start_node_id.clone());
    queue.push_back(VisitedNode {
        node_id: request.start_node_id.clone(),
        depth: 0,
        via_relation: None,
        parent_node_id: None,
    });

    while let Some(node) = queue.pop_front() {
        if visited.len() >= limit {
            break;
        }

        let node_id = node.node_id.clone();
        let depth = node.depth;
        visited.push(node);

        if depth >= request.max_depth {
            continue;
        }

        if let Some(edges) = adjacency.get(&node_id) {
            for edge in edges {
                if visited_ids.insert(edge.to.clone()) {
                    queue.push_back(VisitedNode {
                        node_id: edge.to.clone(),
                        depth: depth + 1,
                        via_relation: empty_relation_as_none(&edge.relation),
                        parent_node_id: Some(node_id.clone()),
                    });
                }
            }
        }
    }

    GraphTraversalResponse {
        request_id: request.request_id,
        start_node_id: request.start_node_id,
        visited,
    }
}

fn build_adjacency(edges: &[GraphEdge]) -> BTreeMap<String, Vec<GraphEdge>> {
    let mut adjacency: BTreeMap<String, Vec<GraphEdge>> = BTreeMap::new();
    for edge in edges {
        adjacency
            .entry(edge.from.clone())
            .or_default()
            .push(edge.clone());
    }

    for edges in adjacency.values_mut() {
        edges.sort();
    }

    adjacency
}

fn empty_relation_as_none(relation: &str) -> Option<String> {
    if relation.is_empty() {
        None
    } else {
        Some(relation.to_string())
    }
}
