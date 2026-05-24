## Summary

-

## Branch Type

- [ ] Feature branch uses `feature/<short-name>`
- [ ] Fix branch uses `fix_<timestamp-or-uuid>`
- [ ] Tests for new behavior live under `tests/`

## Verification

- [ ] `uv run ruff check src/ tests/`
- [ ] `bash scripts/ci-python-stable-tests.sh`
- [ ] `uv run pytest -q` run locally for broader migration coverage when feasible
- [ ] `cd frontend/next-app && npm run build`
- [ ] `cd frontend/next-app && npm run lint`
- [ ] `cd frontend/next-app && npm run typecheck`
- [ ] `cd frontend/next-app && npm run test:race`
- [ ] Rust service checks run when touching `services/**`

## Safety

- [ ] No `.env`, `.secrets/`, tokens, credentials, local databases, or private key files
- [ ] No generated screenshots, image artifacts, PDFs, media files, or bulky local outputs
- [ ] No local worktree, cache, virtualenv, browser trace, or provider proof output directories
- [ ] Dependency changes include `uv.lock`; local command logs stay untracked
- [ ] Any required operator secrets are documented as env names only, never values

## Merge Readiness

- [ ] CI is green
- [ ] Required review is approved
- [ ] Auto-merge can be enabled after branch protection checks are satisfied
