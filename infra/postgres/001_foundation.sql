create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists runs (
    run_id uuid primary key default gen_random_uuid(),
    goal text not null,
    status text not null,
    conversation_state jsonb not null default '{}'::jsonb,
    active_agents text[] not null default '{}',
    source_record_ids uuid[] not null default '{}',
    artifact_ids uuid[] not null default '{}',
    feedback_item_ids uuid[] not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists conversation_turns (
    turn_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    speaker text not null,
    modality text not null,
    transcript text not null,
    audio_uri text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists realtime_sessions (
    realtime_session_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    provider text not null,
    provider_session_id text not null,
    voice text,
    audio_mode text not null default 'speech_to_speech',
    instructions text not null,
    has_client_secret boolean not null default false,
    has_websocket_url boolean not null default false,
    expires_at_unix bigint,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists run_events (
    event_id bigserial primary key,
    run_id uuid not null references runs(run_id) on delete cascade,
    event_type text not null,
    actor text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists run_checkpoints (
    checkpoint_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    checkpoint_kind text not null default 'manual',
    status text not null,
    conversation_state jsonb not null default '{}'::jsonb,
    active_agents text[] not null default '{}',
    source_record_ids uuid[] not null default '{}',
    artifact_ids uuid[] not null default '{}',
    feedback_item_ids uuid[] not null default '{}',
    event_cursor bigint,
    state_digest jsonb not null default '{}'::jsonb,
    created_by text not null default 'agent-harness-engineer',
    notes text,
    created_at timestamptz not null default now()
);

create table if not exists agent_messages (
    message_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    sender_agent_id text not null,
    recipient_agent_id text not null,
    task_type text not null,
    payload jsonb not null default '{}'::jsonb,
    depends_on_message_ids uuid[] not null default '{}',
    requires_human_feedback boolean not null default false,
    status text not null default 'accepted',
    claimed_by_agent_id text,
    attempt_count integer not null default 0,
    max_attempts integer not null default 3,
    result jsonb not null default '{}'::jsonb,
    handoff_trace jsonb not null default '[]'::jsonb,
    error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists source_records (
    source_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    citation_id text not null,
    title text not null,
    url text not null,
    publisher text,
    retrieved_at timestamptz not null default now(),
    published_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    unique (run_id, citation_id)
);

create table if not exists claim_records (
    claim_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    claim_text text not null,
    support_status text not null default 'needs_review',
    source_ids uuid[] not null default '{}',
    reviewer_agent_id text,
    notes text,
    created_at timestamptz not null default now()
);

create table if not exists feedback_items (
    feedback_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    author text not null default 'user',
    target_agent_id text,
    feedback_text text not null,
    status text not null default 'open',
    metadata jsonb not null default '{}'::jsonb,
    resolution_notes text,
    resolved_by text,
    resolved_at timestamptz,
    updated_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists artifacts (
    artifact_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    artifact_type text not null,
    title text not null,
    uri text not null,
    content jsonb not null default '{}'::jsonb,
    provenance jsonb not null default '{}'::jsonb,
    source_ids uuid[] not null default '{}',
    reviewer_decisions jsonb not null default '[]'::jsonb,
    revision_history jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists guardrail_audits (
    audit_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    artifact_id uuid not null references artifacts(artifact_id) on delete cascade,
    status text not null,
    source_coverage double precision not null default 0,
    claim_count integer not null default 0,
    supported_claim_ids uuid[] not null default '{}',
    needs_review_claim_ids uuid[] not null default '{}',
    unsupported_claim_ids uuid[] not null default '{}',
    missing_source_claim_ids uuid[] not null default '{}',
    blocking_issues text[] not null default '{}',
    reviewer_agent_id text not null default 'guardrails-agent',
    notes text not null,
    created_at timestamptz not null default now()
);

create table if not exists agent_memories (
    memory_id uuid primary key default gen_random_uuid(),
    agent_id text not null,
    run_id uuid references runs(run_id) on delete set null,
    memory_kind text not null,
    content text not null,
    embedding vector,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists retrieval_candidates (
    candidate_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    source_id uuid references source_records(source_id) on delete set null,
    query text,
    retriever text not null,
    rank integer,
    score double precision,
    fused_rank integer,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists retrieval_rerank_decisions (
    decision_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    candidate_id uuid references retrieval_candidates(candidate_id) on delete cascade,
    reranker text not null,
    rank_before integer,
    rank_after integer,
    relevance_score double precision,
    accepted_for_context boolean not null default false,
    reason text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists knowledge_graph_nodes (
    node_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    node_type text not null,
    label text not null,
    source_ids uuid[] not null default '{}',
    claim_ids uuid[] not null default '{}',
    artifact_ids uuid[] not null default '{}',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists knowledge_graph_edges (
    edge_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    from_node_id uuid not null references knowledge_graph_nodes(node_id) on delete cascade,
    to_node_id uuid not null references knowledge_graph_nodes(node_id) on delete cascade,
    relationship text not null,
    confidence double precision,
    source_ids uuid[] not null default '{}',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists retrieval_evaluations (
    evaluation_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    topic text not null,
    status text not null,
    candidate_count integer not null default 0,
    accepted_candidate_count integer not null default 0,
    precision_risk_count integer not null default 0,
    recall_gap_count integer not null default 0,
    coverage_gap_count integer not null default 0,
    recommended_queries text[] not null default '{}',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists worker_profiles (
    profile_id uuid primary key default gen_random_uuid(),
    run_id uuid not null references runs(run_id) on delete cascade,
    name text not null,
    execution_mode text not null default 'worker_cycle',
    agent_ids text[] not null default '{}',
    max_tasks_per_agent integer not null default 1,
    max_rounds integer not null default 1,
    poll_interval_seconds double precision not null default 5.0,
    include_global_memories boolean not null default true,
    memory_limit integer not null default 6,
    autonomous_auto_refresh_research_sources boolean not null default true,
    autonomous_block_on_research_freshness_blocked boolean not null default true,
    autonomous_block_on_retrieval_quality_blocked boolean not null default true,
    autonomous_export_memory_summary_to_obsidian boolean not null default false,
    autonomous_memory_summary_agent_id text,
    autonomous_memory_summary_limit integer not null default 8,
    use_gemma boolean not null default true,
    fail_on_provider_error boolean not null default false,
    status text not null default 'paused',
    last_heartbeat_at timestamptz,
    heartbeat_claimed_at timestamptz,
    heartbeat_claimed_by text,
    heartbeat_lease_until timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table artifacts
    add column if not exists content jsonb not null default '{}'::jsonb;

alter table agent_messages
    add column if not exists depends_on_message_ids uuid[] not null default '{}',
    add column if not exists claimed_by_agent_id text,
    add column if not exists attempt_count integer not null default 0,
    add column if not exists max_attempts integer not null default 3,
    add column if not exists result jsonb not null default '{}'::jsonb,
    add column if not exists handoff_trace jsonb not null default '[]'::jsonb,
    add column if not exists error text,
    add column if not exists updated_at timestamptz not null default now();

alter table feedback_items
    add column if not exists metadata jsonb not null default '{}'::jsonb,
    add column if not exists resolution_notes text,
    add column if not exists resolved_by text,
    add column if not exists resolved_at timestamptz,
    add column if not exists updated_at timestamptz not null default now();

alter table worker_profiles
    add column if not exists execution_mode text not null default 'worker_cycle',
    add column if not exists autonomous_auto_refresh_research_sources boolean not null default true,
    add column if not exists autonomous_block_on_research_freshness_blocked boolean not null default true,
    add column if not exists autonomous_block_on_retrieval_quality_blocked boolean not null default true,
    add column if not exists autonomous_export_memory_summary_to_obsidian boolean not null default false,
    add column if not exists autonomous_memory_summary_agent_id text,
    add column if not exists autonomous_memory_summary_limit integer not null default 8,
    add column if not exists heartbeat_claimed_at timestamptz,
    add column if not exists heartbeat_claimed_by text,
    add column if not exists heartbeat_lease_until timestamptz;

create index if not exists idx_runs_status on runs(status);
create index if not exists idx_conversation_turns_run_id_created_at
    on conversation_turns(run_id, created_at);
create unique index if not exists idx_conversation_turns_voice_agent_user_turn
    on conversation_turns(run_id, speaker, (metadata->>'voice_agent_turn_id'))
    where speaker = 'user'
      and metadata->>'voice_agent_event_type' = 'voice_user_turn_committed'
      and coalesce(metadata->>'voice_agent_turn_id', '') <> '';
create unique index if not exists idx_conversation_turns_voice_agent_response
    on conversation_turns(run_id, speaker, (metadata->>'voice_agent_response_id'))
    where speaker = 'assistant'
      and metadata->>'voice_agent_event_type' = 'assistant_response_completed'
      and coalesce(metadata->>'voice_agent_response_id', '') <> '';
create index if not exists idx_realtime_sessions_run_id_created_at
    on realtime_sessions(run_id, created_at);
create index if not exists idx_realtime_sessions_status_updated_at
    on realtime_sessions(status, updated_at);
create index if not exists idx_run_events_run_id_event_id
    on run_events(run_id, event_id);
create index if not exists idx_run_events_run_id_event_type_event_id
    on run_events(run_id, event_type, event_id);
create index if not exists idx_run_checkpoints_run_id_created_at
    on run_checkpoints(run_id, created_at desc);
create index if not exists idx_agent_messages_run_id_created_at
    on agent_messages(run_id, created_at);
create index if not exists idx_agent_messages_recipient_status
    on agent_messages(recipient_agent_id, status);
create index if not exists idx_agent_messages_status_updated_at
    on agent_messages(status, updated_at);
create index if not exists idx_agent_messages_depends_on_gin
    on agent_messages using gin(depends_on_message_ids);
create index if not exists idx_source_records_run_id
    on source_records(run_id);
create index if not exists idx_claim_records_run_id_support
    on claim_records(run_id, support_status);
create index if not exists idx_feedback_items_run_id_status
    on feedback_items(run_id, status);
create index if not exists idx_artifacts_run_id_type
    on artifacts(run_id, artifact_type);
create index if not exists idx_guardrail_audits_run_id_status
    on guardrail_audits(run_id, status);
create index if not exists idx_guardrail_audits_artifact_id_created_at
    on guardrail_audits(artifact_id, created_at);
create index if not exists idx_agent_memories_agent_id_kind
    on agent_memories(agent_id, memory_kind);
create index if not exists idx_retrieval_candidates_run_id_query
    on retrieval_candidates(run_id, query);
create index if not exists idx_retrieval_candidates_source_id
    on retrieval_candidates(source_id);
create index if not exists idx_retrieval_rerank_decisions_run_id
    on retrieval_rerank_decisions(run_id, created_at);
create index if not exists idx_retrieval_rerank_decisions_candidate_id
    on retrieval_rerank_decisions(candidate_id);
create index if not exists idx_knowledge_graph_nodes_run_id_type
    on knowledge_graph_nodes(run_id, node_type);
create index if not exists idx_knowledge_graph_nodes_source_ids_gin
    on knowledge_graph_nodes using gin(source_ids);
create index if not exists idx_knowledge_graph_nodes_claim_ids_gin
    on knowledge_graph_nodes using gin(claim_ids);
create index if not exists idx_knowledge_graph_edges_run_id_relationship
    on knowledge_graph_edges(run_id, relationship);
create index if not exists idx_retrieval_evaluations_run_id_created_at
    on retrieval_evaluations(run_id, created_at desc);
create index if not exists idx_worker_profiles_run_id_status
    on worker_profiles(run_id, status);
create index if not exists idx_worker_profiles_status_heartbeat
    on worker_profiles(status, last_heartbeat_at);
create index if not exists idx_worker_profiles_heartbeat_lease
    on worker_profiles(status, heartbeat_lease_until);

-- LangGraph's Postgres checkpointer manages its own checkpoint tables during
-- runtime setup. This schema owns the application state around those checkpoints.
