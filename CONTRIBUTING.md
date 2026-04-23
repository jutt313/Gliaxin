# Contributing to Gliaxin OSS

Thanks for taking the time. A few ground rules to keep things clean.

## Reporting bugs

Open an issue and include:
- What you ran
- What you expected
- What actually happened
- Your OS, Python version, and which LLM provider you're using

## Submitting a change

1. Fork the repo and create a branch from `main`
2. Make your change — keep it focused, one thing per PR
3. Test it locally against a running Gliaxin instance before opening the PR
4. Open the PR with a short description of what changed and why

## What's in scope

- Bug fixes in the backend, worker, or integrations
- New LLM provider implementations (follow `oss/backend/src/providers/base.py`)
- Improvements to existing agent integrations
- Docs fixes

## What's out of scope

- SaaS features, multi-tenant flows, billing, Firebase — none of that belongs here
- Anything that adds a required cloud dependency

## Code style

- Python: follow what's already there, no formatter required
- TypeScript: same
- No new dependencies without a good reason

## Questions

Open an issue and ask. That's what they're for.
