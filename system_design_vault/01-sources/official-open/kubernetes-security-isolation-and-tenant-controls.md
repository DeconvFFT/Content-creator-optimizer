---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://kubernetes.io/docs/concepts/security/rbac-good-practices/
  - https://kubernetes.io/docs/concepts/security/secrets-good-practices/
  - https://kubernetes.io/docs/concepts/security/service-accounts/
  - https://kubernetes.io/docs/concepts/security/multi-tenancy/
  - https://kubernetes.io/docs/concepts/services-networking/network-policies/
source_status: official_public
verification_notes:
  - Kubernetes current docs opened directly on 2026-05-18; docs version selector showed v1.36.
  - This note stores original synthesis only and does not copy source text or examples.
---

# Kubernetes Security Isolation And Tenant Controls

## Direct-Read Scope

Direct-read pass over official Kubernetes RBAC good practices, Secrets good practices, Service Accounts, Multi-tenancy, and Network Policies docs.

This note fills the infrastructure isolation gap under Agent Studio's GenAI security canon. Prompt-injection defenses and tool approvals are necessary, but they are not sufficient if every worker, connector, or route shares the same service identity, credentials, namespace, network reachability, and secret access.

## Core Read

Kubernetes RBAC good practice is least privilege plus escalation awareness. RBAC is not just a list of allowed verbs; some verbs and resources create escalation paths. Listing Secrets exposes secret values. Creating workloads can expose mounted Secrets. `bind`, `escalate`, `impersonate`, certificate-signing, token requests, node proxy access, and broad workload creation are high-risk privileges. For Agent Studio, that means "read-only" and "admin" are not enough permission classes. The route ledger needs to know which permissions can indirectly become credential access, cluster access, or external side effects.

Service Accounts are workload identities. They should receive the minimum permissions required for the workload, and different workloads should not reuse one broad identity. Agent Studio should map each route lane to a workload identity: source extraction, embedding/indexing, realtime voice, model serving, browser/computer-use, publishing, eval judging, and maintenance should not all run as the same principal.

Secrets require tighter handling than ordinary configuration. Access to list/watch Secrets is effectively access to many secrets. A user or workload that can create a Pod mounting a Secret may be able to expose that Secret even without direct read permission. Multi-container Pods should mount credentials only into containers that need them. Agent Studio should therefore treat credential access as a side-effect surface, not as ambient environment.

Multi-tenancy guidance makes namespaces, RBAC, quotas, and network policy work together. Namespaces provide management separation; RBAC restricts who can operate in each namespace; quotas protect fairness and control-plane health; network policies prevent accidental or malicious cross-tenant traffic. For Agent Studio, "tenant" can mean user, project, source corpus, route class, environment, or customer. The product should not wait for enterprise multi-tenancy before modeling these boundaries.

NetworkPolicies control layer 3/4 traffic only when the cluster network plugin enforces them. Without an enforcing plugin, creating a policy resource does nothing. Kubernetes also allows broad pod-to-pod traffic by default. Agent Studio should therefore record both intended network policy and enforcement evidence. A route that can reach every internal service is overprivileged even if its prompt says it should not.

## Current-Source Cross-Check

Current Kubernetes v1.36 docs preserve the same control-plane shape. RBAC good practices still frame least privilege around escalation paths such as secret access, workload creation, token requests, impersonation, bind/escalate, and node/proxy-style powers. Secrets guidance still treats broad secret read/list/watch and pod-mounted credentials as high-risk, and Service Accounts remain the workload identity surface that should be scoped per workload rather than shared broadly.

Current multi-tenancy and NetworkPolicy guidance still separates namespace/workspace boundaries, RBAC, quotas, and network isolation. NetworkPolicy remains conditional on an enforcing network plugin, and default pod networking is not a default-deny security boundary. For Agent Studio, the cross-check is that infrastructure isolation must be release evidence: a route with private sources, connectors, publishing credentials, browser/computer-use, or code execution needs real identity, credential, tenant, and network constraints underneath model-level guardrails.

## Agent Studio Design Implications

- Use route-specific workload identities. Source ingestion, publishing, browser/computer-use, media generation, evals, and realtime voice should have separate service accounts or equivalent principals.
- Treat permissions as graph edges. A route with workload creation, secret mount, token request, impersonation, or bind/escalate capability can cross boundaries even if it lacks direct secret-read permission.
- Store secret access as a reviewed capability: secret name/scope, mounted container or process, rotation policy, last use, and allowed route surfaces.
- Do not let generated code, tool plugins, or connector servers run with shared privileged credentials by default.
- Separate tenants and trust zones at the namespace/project/workspace layer: user-private sources, public official sources, generated artifacts, publishing connectors, and eval jobs should not all share one flat environment.
- Apply default-deny thinking for network paths: workers get explicit egress/ingress needs rather than broad internal reachability.
- Record network policy enforcement evidence. A written policy is not a control unless the runtime actually enforces it.
- For local-first development, model the same boundaries even when they are implemented as local process permissions, filesystem scopes, env vars, sandbox profiles, or connector allowlists instead of Kubernetes objects.
- Add periodic permission review. Permissions drift as tools, routes, and connectors are added; the release ledger should detect broad bindings and stale credentials.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `workload_identity_record` | Service account or local principal used by a route/worker with owner, scope, permissions, and last-used evidence. |
| `rbac_permission_binding` | Permission edge from subject to verb/resource/scope with escalation risk classification and review status. |
| `secret_access_record` | Secret/credential access contract with secret scope, consumer, mount/injection method, rotation, and least-privilege review. |
| `tenant_isolation_boundary` | User/project/corpus/route/environment boundary with namespace/workspace, quota, RBAC, network, and data-sensitivity policy. |
| `network_policy_record` | Intended and enforced network path policy for route workers, providers, databases, queues, MCP servers, and publishing connectors. |
| `permission_review_record` | Periodic audit of identities, broad grants, stale credentials, secret access, network reachability, and remediation. |
| `privilege_escalation_risk` | Explicit risk record for permissions such as secret list/watch, workload create, token request, bind, escalate, impersonate, or node proxy. |
| `infrastructure_isolation_release_gate` | Promotion gate proving runtime authority boundaries before privileged route launch. |

Minimum fields for `infrastructure_isolation_release_gate`: `gate_id`, `route_id`, `workload_identity_ref`, `rbac_permission_binding_refs`, `privilege_escalation_risk_refs`, `secret_access_refs`, `tenant_isolation_boundary_ref`, `network_policy_refs`, `network_enforcement_evidence_ref`, `pod_or_runtime_security_policy_ref`, `audit_log_ref`, `permission_review_ref`, `rollback_or_revoke_plan_ref`, `decision`, `reviewed_at`.

## Release Gate

A privileged Agent Studio route cannot launch or increase autonomy unless an `infrastructure_isolation_release_gate` proves separate workload identity, least-privilege RBAC, escalation-risk review, scoped secret access, tenant/workspace boundary, default-deny or explicitly bounded network reachability, network-policy enforcement evidence, pod/runtime security posture, audit evidence, permission-review cadence, and a revoke/rollback plan. Prompt policy, tool approvals, or guardrail evals do not compensate for broad shared credentials.

## Canon Decision

This note is canon-ready for Agent Studio privileged runtime design. Agent Studio should not rely on prompt policy to contain privileged infrastructure. Every route needs a workload identity, permission boundary, secret-access record, network reachability contract, and tenant/workspace boundary appropriate to its risk. Security release gates should prove both model behavior and infrastructure isolation: a safe refusal is not enough if the route still runs with broad credentials or unrestricted network access.
