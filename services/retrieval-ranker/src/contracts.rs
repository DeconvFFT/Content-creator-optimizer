use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum RetrievalRankerRequest {
    Rank(RankRequest),
    TraverseGraph(GraphTraversalRequest),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum RetrievalRankerResponse {
    Rank(RankResponse),
    TraverseGraph(GraphTraversalResponse),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RankRequest {
    #[serde(default)]
    pub request_id: Option<String>,
    pub query: String,
    #[serde(default)]
    pub candidates: Vec<Candidate>,
    #[serde(default)]
    pub config: ScoringConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Candidate {
    pub id: String,
    pub text: String,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub source_uri: Option<String>,
    #[serde(default)]
    pub metadata: BTreeMap<String, String>,
    #[serde(default)]
    pub signals: CandidateSignals,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct CandidateSignals {
    #[serde(default)]
    pub vector_score: Option<f64>,
    #[serde(default)]
    pub lexical_score: Option<f64>,
    #[serde(default)]
    pub graph_distance: Option<u32>,
    #[serde(default)]
    pub authority: Option<f64>,
    #[serde(default)]
    pub freshness_days: Option<u32>,
}

impl Default for CandidateSignals {
    fn default() -> Self {
        Self {
            vector_score: None,
            lexical_score: None,
            graph_distance: None,
            authority: None,
            freshness_days: None,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct ScoringConfig {
    #[serde(default = "default_vector_weight")]
    pub vector_weight: f64,
    #[serde(default = "default_lexical_weight")]
    pub lexical_weight: f64,
    #[serde(default = "default_graph_weight")]
    pub graph_weight: f64,
    #[serde(default = "default_authority_weight")]
    pub authority_weight: f64,
    #[serde(default = "default_freshness_weight")]
    pub freshness_weight: f64,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

impl Default for ScoringConfig {
    fn default() -> Self {
        Self {
            vector_weight: default_vector_weight(),
            lexical_weight: default_lexical_weight(),
            graph_weight: default_graph_weight(),
            authority_weight: default_authority_weight(),
            freshness_weight: default_freshness_weight(),
            limit: default_limit(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RankResponse {
    #[serde(default)]
    pub request_id: Option<String>,
    pub results: Vec<RankedCandidate>,
    pub diagnostics: RankDiagnostics,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RankedCandidate {
    pub id: String,
    pub rank: usize,
    pub score: f64,
    pub source_uri: Option<String>,
    pub metadata: BTreeMap<String, String>,
    pub explanation: ScoreBreakdown,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct ScoreBreakdown {
    pub vector_component: f64,
    pub lexical_component: f64,
    pub graph_component: f64,
    pub authority_component: f64,
    pub freshness_component: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RankDiagnostics {
    pub candidate_count: usize,
    pub returned_count: usize,
    pub scoring_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphTraversalRequest {
    #[serde(default)]
    pub request_id: Option<String>,
    pub start_node_id: String,
    #[serde(default = "default_max_depth")]
    pub max_depth: u32,
    #[serde(default = "default_graph_limit")]
    pub limit: usize,
    #[serde(default)]
    pub edges: Vec<GraphEdge>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub struct GraphEdge {
    pub from: String,
    pub to: String,
    #[serde(default)]
    pub relation: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphTraversalResponse {
    #[serde(default)]
    pub request_id: Option<String>,
    pub start_node_id: String,
    pub visited: Vec<VisitedNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VisitedNode {
    pub node_id: String,
    pub depth: u32,
    pub via_relation: Option<String>,
    pub parent_node_id: Option<String>,
}

fn default_vector_weight() -> f64 {
    0.45
}

fn default_lexical_weight() -> f64 {
    0.25
}

fn default_graph_weight() -> f64 {
    0.15
}

fn default_authority_weight() -> f64 {
    0.10
}

fn default_freshness_weight() -> f64 {
    0.05
}

fn default_limit() -> usize {
    20
}

fn default_max_depth() -> u32 {
    2
}

fn default_graph_limit() -> usize {
    100
}
