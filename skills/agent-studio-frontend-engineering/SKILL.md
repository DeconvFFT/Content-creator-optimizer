---
name: agent-studio-frontend-engineering
description: "Build and review the Agent Studio frontend. Use when implementing the conversational cockpit, voice controls, event streaming, source-ledger drilldowns, artifact previews, feedback gates, accessibility, or separate generated planning viewers."
---

# Agent Studio Frontend Engineering

## Workflow

1. Confirm the surface boundary before implementation: product cockpit, generated planning viewer, or Obsidian companion artifact.
2. For the product cockpit, optimize for live conversation, draft review, source inspection, artifact browsing, feedback controls, voice settings, provider readiness, and run activity.
3. Keep planning and design inspection surfaces separate from the product app.
4. Render UI state from durable APIs instead of embedding hidden local state that becomes a second source of truth.
5. Use responsive, accessible controls for voice/text input, source drilldowns, feedback approval, and run inspection.
6. Keep visible UI copy task-oriented and concise; do not add in-app explanations of the whole architecture.
7. After UI edits, run syntax checks and browser smoke checks when practical.
8. Record important UI decisions and operator feedback in Obsidian.

## Quality Targets

- Natural dialogue stays central: the first screen should feel like a live conversational studio.
- Source and artifact state is inspectable without turning the app into a project-management dashboard.
- Voice controls, feedback gates, and run timeline states remain clear on desktop and mobile.
- Generated HTML viewers explain architecture, but Obsidian remains the planning source of truth.

## Outputs

- `frontend_implementation_plan`
- `ui_state_contract`
- `accessibility_notes`
- `cockpit_surface_review`
- `browser_smoke_result`
