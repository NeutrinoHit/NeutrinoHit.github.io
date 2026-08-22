# NeutrinoHit repository rules

## Git policy

- GitHub is read-only for assistants and workers.
- Never commit, push, create branches, PRs, issues, or releases.
- Return findings, patches/diffs, validation commands, and unresolved risks.
- Dmitry performs integration.

## Repository structure

- NeutrinoHit consists of independent Git repositories.
- Do not turn repositories into a monorepo.
- Do not move content between repositories without explicit request.

## Build

- Read the current repository before making changes.
- Use existing Makefile targets as the build entry point.
- Do not duplicate project-specific build logic in workflows.
- Generated outputs are not source files unless explicitly documented.

## Documentation

- Do not add AI metadata, agent instructions, prompts, or generated-by markers.
- Avoid boilerplate documentation.
- Do not invent files, URLs, translations, or publication states.

## Worker output

Return:

1. Findings.
2. Proposed change.
3. Patch/diff.
4. Validation commands.
5. Unresolved risks.
