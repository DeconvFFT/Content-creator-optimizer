# Next.js Content Generation App

Production-oriented frontend scaffold for the source-backed content-generation workflow. It is intentionally separate from `frontend/cockpit/` and focuses on the creator-facing loop: text or voice input, grounded draft review, per-draft actions, and revision feedback.

## Run locally

```bash
cd frontend/next-app
cp .env.example .env.local
npm install
npm run dev
```

The app expects FastAPI at `http://127.0.0.1:8000` by default. For normal local validation, keep browser requests same-origin through the Next `/api/*` proxy:

```bash
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --hostname 127.0.0.1 --port 3000
```

Use `NEXT_API_PROXY_TARGET` when FastAPI is on a non-default local port. Do not set `NEXT_PUBLIC_API_BASE_URL` for same-machine validation unless FastAPI is configured for browser CORS, because that makes the browser call the API origin directly instead of using the Next proxy.

For a production-build local proof against a validation backend:

```bash
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001 npm run build
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001 npm run start -- -H 127.0.0.1 -p 3003
```

## Validation

```bash
npm run typecheck
npm run lint
npm run build
npm run test:browser-single-flight
```

`test:browser-single-flight` starts the local Next app on an ephemeral port,
mocks the FastAPI boundary in Chromium, and rapidly double-clicks the creator
Create voice run, Generate, Run web research, Suggest next step, Publish check,
Send revision, and Start transcript rehearsal controls. It proves the voice-first starter creates exactly
one voice-mode `POST /api/runs` payload with Gemma 4 E4B/Kokoro provenance,
refreshes the same run context, hides the no-run starter, and binds the next
Generate turn to that run. It then rapidly double-clicks Runtime preflight and
proves the browser sends one full LiveKit/Gemma/Kokoro preflight readiness
request. It also rapidly double-clicks Check setup and proves the setup fanout
records one durable voice setup proof after one LiveKit process refresh, one
voice-agent process refresh, one provider-readiness refresh, one runtime
preflight, and one voice-agent presence check. It then rapidly double-clicks
Runtime smoke and Timing ledger to prove the browser records one non-live
provider-smoke request and one realtime timing-ledger request without promoting
either blocked proof to provider-backed live voice readiness; the smoke also
cross-clicks the two proof buttons in both orders to prove one in-flight proof
action blocks the other. It switches to Transcript rehearsal and rapidly
double-clicks Start transcript rehearsal to prove exactly one dry-run realtime
session request is created for local rehearsal, then rapidly double-clicks
Route rehearsal turn to prove one non-production realtime-turn request with
rehearsal-only metadata.
It also runs `Queue and run` from a failed specialist task and runs
`Run next steps` after a suggested work plan. It proves source-refresh A2A message creation,
the source-refresh bounded worker cycle, targeted retry worker cycle execution,
work-plan materialization, planned worker execution, and post-run plan refresh.
Those actions each run only once after rapid duplicate clicks. It also clicks
Start always-on and Start runner with mocked stale backend summaries, then
asserts the browser shows creator-facing Always-on studio and Background runner
status copy instead of raw Autopilot or local scheduler wording. Together this
proves the browser-visible single-flight guards create only one backend action
per rapid duplicate submit
and that the high-risk always-on status surface keeps product language.

This script uses the Python `playwright` dev extra and requires the Chromium
browser install (`python -m playwright install chromium`) in a clean checkout.

## API boundary

Backend contracts live in `lib/api/types.ts`, and all fetch calls are centralized in `lib/api/client.ts`. UI components should not build raw FastAPI URLs directly.
