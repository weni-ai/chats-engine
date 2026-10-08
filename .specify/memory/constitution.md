<!--
Sync Impact Report:
- Version change: none (template) → 1.0.0
- Modified principles: none (first generation)
- Added principles:
  I. Version Control and Review
  II. Security and Secrets
  III. Observability
  IV. Versioned Contracts
  V. Specification Traceability
  VI. No Silent Divergence
  VII. Commit Messages
  VIII. Changelog Maintenance
  IX. Never Trust the Client
  X. Fail Gracefully and Predictably
  XI. Bounded Retry Over REST
  XII. Scalability and Peak Load
  XIII. Diagnosable Errors
  XIV. Tests Exercise Flows
  XV. Explicit Over Clever
  XVI. Contained Changes
- Added sections: Technology Stack and Constraints, Development Workflow and Quality Gates, Governance
- Removed sections: none
- Templates requiring updates: none (.specify/templates and .specify/scripts left untouched)
- Follow-up TODOs: none

Provenance:
- Source: weni-ai/vtex-cx-engineering-constitutions (main)
- Files: base-constitution.md, backend/base-constitution.md
- Domains: backend
-->

# Chats Engine Constitution

Chats Engine provides the REST and WebSocket APIs for the Weni customer service
module (Django, Django REST Framework, Channels, Celery). This constitution binds
every change to this repository. Principles I–VIII come from the root
engineering constitution and prevail on conflict; principles IX–XVI specialize
them for backend services and MUST NOT contradict them.

## Core Principles

### I. Version Control and Review

All code MUST enter `main` through a pull request. A merge MUST require at
least one approved review and a green CI run (`.github/workflows/ci.yaml`).
Direct pushes to `main` MUST be blocked via platform branch protection, and the
`no-commit-to-branch` pre-commit hook MUST remain enabled.

**Rationale:** the policy is only real when enforced by the platform, not by
trust. Peer review and a protected main branch keep history auditable and
prevent unreviewed changes from reaching production.

### II. Security and Secrets

Secrets MUST never be committed to the repository; `.env` files, keys, tokens,
and connection strings MUST stay out of version control. Secrets MUST be
provided by an external secrets manager and injected at runtime as environment
variables. Values in CI workflows MUST be non-production dummies. The
`detect-aws-credentials` and `detect-private-key` pre-commit hooks MUST NOT be
skipped. Access MUST follow least privilege by default. Dependencies MUST come
only from trusted sources, MUST be pinned through `poetry.lock`, and MUST be
checked for known vulnerabilities.

**Rationale:** leaked credentials and untrusted dependencies are among the most
common and most damaging breaches; prevention is far cheaper than remediation.

### III. Observability

Logs MUST be structured and MUST never contain secrets or sensitive personal
data (contact names, e-mails, phone numbers, message contents). Errors MUST be
traceable across components — HTTP requests, WebSocket consumers, Celery tasks,
and event-driven consumers — through correlation or trace identifiers.

**Rationale:** structured, privacy-safe telemetry is what makes incidents
diagnosable without creating new data-exposure risks.

### IV. Versioned Contracts

Any change to a public interface — REST endpoints under `chats/apps/api/v1` and
`chats/apps/api/v2`, internal and external APIs, WebSocket message payloads, and
published events — MUST be versioned. REST APIs are versioned by path
(`v1`, `v2`); a breaking change MUST go to a new path version. Changes MUST be
backward compatible within the same API version or ship with an announced
deprecation path. Silent breaking changes MUST NOT be introduced.

**Rationale:** consumers depend on stable contracts; explicit versioning and
deprecation give them a predictable path to adapt without outages.

### V. Specification Traceability

Every engineering spec under `specs/` MUST derive from exactly one approved
product spec and MUST reference it through an immutable, pinned version (commit
or tag) — a mutable URL or ID alone MUST NOT be used. The product spec MUST
exist and be tagged before its engineering spec is created. An engineering spec
MUST NOT redefine the "what" it inherits: problem, scope, success criteria, and
binding decisions belong to the product spec. A technical architecture document
SHOULD be produced for non-trivial features; when it exists it MUST be linked
from the engineering spec, also pinned by commit/tag, but its absence MUST NOT
block the engineering spec.

Every engineering spec MUST open with an inheritance section in exactly this
format:

```
## Inheritance from Product Spec
- Product Spec: <title> — <URL>
- Pinned version: <commit/tag>
- Architecture doc: <none | URL + commit/tag>
- Inherited binding decisions: <short list>
- Scope of this spec: <slice implemented by this repo>
- Divergences: <none | link to amendment>
```

**Rationale:** traceability from product intent to technical execution keeps
decisions auditable and lets any change be traced back to the need that
justified it. Pinning the version guarantees every team implements the same
version of the feature. Making the product spec mandatory prevents engineering
work without an agreed problem; keeping the architecture doc optional avoids
blocking delivery on ceremony. A single inheritance format keeps the link
machine-checkable and uniform across repositories.

### VI. No Silent Divergence

When a technical need contradicts something inherited from the product spec —
scope, success criteria, or a binding decision — the divergence MUST NOT be
implemented silently in code. It MUST be raised as an amendment in the product
repository and recorded in the `Divergences` field of the engineering spec's
inheritance section, linking to that amendment. Once the amendment is approved
and produces a new tag, the engineering spec's `Pinned version` MUST be updated
to it. A technical difference that contradicts nothing inherited is not a
divergence but an implementation decision, and MUST live in the engineering
spec.

**Rationale:** when the product spec is the single source of truth, a silent
code deviation makes intent and implementation drift apart with no audit trail.
Forcing divergences through amendments keeps the spec authoritative.

### VII. Commit Messages

Commits MUST follow Conventional Commits format: `<type>: <description>`.
Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`. The
description MUST be imperative, specific, and no longer than 50 characters.
Commits MUST be atomic: one logical change per commit.

**Rationale:** conventional commits enable automated changelog generation and
semantic versioning. Atomic commits simplify bisecting, reverting, and
reviewing.

### VIII. Changelog Maintenance

Public libraries MUST maintain a changelog following Keep a Changelog format.
Every user-facing change MUST appear in the changelog under the appropriate
category (Added, Changed, Deprecated, Removed, Fixed, Security). Version bumps
MUST follow SemVer. This repository is a service, not a public library; its
`CHANGELOG.md` uses its own format (`# <version>` followed by `# Add`, `# Fix`,
`# Refactor` entries).

**Rationale:** a well-maintained changelog communicates impact to consumers and
serves as release documentation. SemVer alignment ensures predictable upgrade
expectations.

### IX. Never Trust the Client

Everything that reaches the server from outside — the web frontend, WebSocket
clients, third-party webhooks, other Weni services, or event-driven messages —
MUST be treated as potentially malicious, incomplete, or incorrect until it is
rigorously validated. Every external input MUST be validated for type, format,
range, and business rules at the server boundary (DRF serializers, WebSocket
consumers, event parsers) before use. Authorization MUST be enforced on the
server for every request through DRF permissions or equivalent checks,
regardless of any check already performed by the client.

**Rationale:** clients run outside the server's control and can be inspected,
modified, or bypassed. Treating external input as untrusted until validated
prevents injection, data corruption, and privilege-escalation attacks that
client-side checks alone can never stop.

### X. Fail Gracefully and Predictably

Calls to external dependencies — HTTP integrations, AI providers, storage,
message brokers, Redis, and the database — MUST have explicit timeouts and MUST
NOT block indefinitely. Failures MUST be handled explicitly and surfaced as
consistent, well-defined error responses — never as unhandled crashes or leaked
internal details such as stack traces or upstream payloads.

**Rationale:** failure is a certainty, not an edge case. Handling it explicitly
and predictably keeps partial outages contained and observable instead of
letting one failing dependency take down the whole system or expose internals
to callers.

### XI. Bounded Retry Over REST

When data is propagated between services over a REST call, a failure in that
call MUST be retried rather than dropped. A retry MUST be attempted only when
the failure could plausibly succeed on another attempt — a connection error, a
request timeout, an HTTP 5xx, or an HTTP 429 — and MUST NOT be attempted on a
4xx that reflects a defect in the request itself. A retry MUST only be applied
to an operation that is idempotent or protected by a deduplication key; when
the operation is neither, it MUST be made idempotent rather than left without
retry. Every retry policy, including Celery task retries, MUST define a maximum
number of attempts and a backoff strategy; unbounded retry MUST NOT be used.
When the attempts are exhausted, the failure MUST be logged and MUST remain
recoverable — it MUST NOT be silently discarded.

**Rationale:** propagation between services fails for transient reasons far
more often than for permanent ones, so retrying keeps services converging.
Retrying a rejected request multiplies load for nothing, and retrying a
non-idempotent operation duplicates its effect. Bounds keep the mechanism from
becoming the outage, and a recoverable exhausted case prevents data from
disappearing between two services that each believe they succeeded.

### XII. Scalability and Peak Load

Every process — web/ASGI workers, WebSocket consumers, Celery workers, and
event consumers — MUST be stateless so that it can scale horizontally: state
that outlives a single request or message MUST NOT be kept in process memory or
on local disk, and MUST live in an external store shared by all instances
(PostgreSQL, Redis, object storage). The peak load a feature is expected to
sustain MUST be declared in its engineering spec, stated as peak and not as
average.

**Rationale:** capacity is a design input, not something to be discovered
during an incident. Sizing for average traffic guarantees failure precisely
when demand matters most. Statelessness is what makes adding instances a valid
answer to load; declaring the peak turns scalability into a number that can be
reviewed and tested against.

### XIII. Diagnosable Errors

Every error reported to the error-tracking system (Sentry) MUST carry enough
context to be located and filtered without reproducing it: at minimum the
project identifier, the account identifier, the user identifier, and the
correlation identifier of the request. Those identifiers MUST be opaque (UUIDs,
not e-mails or names). Sensitive personal data — names, e-mail addresses, phone
numbers, government identifiers, or message contents — MUST NOT be attached to
an error report under any circumstance.

**Rationale:** an error without identifying context can be counted but not
investigated. Opaque identifiers give exactly the filtering an investigation
needs while keeping the report free of personal data, as Principle III
requires.

### XIV. Tests Exercise Flows

Every flow — REST endpoint, WebSocket interaction, Celery task, or event
consumer — MUST have at least one test covering the complete use case, from
input to resulting effect. Tests that assert a single method in isolation are
allowed and SHOULD be used to explore edge cases and input variations that are
expensive to reach through the whole flow, but they MUST NOT be the only
coverage a flow has. Every flow MUST cover its success path and its failure
paths; an error path that no test exercises MUST NOT be considered covered.
Test files MUST follow the `name-tests-test --django` naming convention
(`test*.py`).

**Rationale:** a suite made only of isolated method tests can be green while
the composition of those methods is broken. Method-level tests remain the
cheapest way to cover many inputs, so this rule is additive. Failure paths are
the least exercised in development and the most expensive in production.

### XV. Explicit Over Clever

What a piece of code does MUST be evident where it happens. Hidden side effects
and implicit control flow MUST NOT be introduced to save lines. Any literal that carries
meaning — a threshold, a limit, a timeout, a retry count — MUST be a named
constant or a setting rather than an inline value. A literal that carries no
meaning beyond its own value, such as an index of 0 or an increment of 1, is
exempt. Comments MUST explain why a decision was made: the constraint, the
trade-off, or the non-obvious reason behind it. A comment that restates what
the code already says is a signal that the code SHOULD be rewritten to say it.

**Rationale:** code is read far more often than it is written, usually by
someone without the original context. An unexplained literal is a decision
nobody can review. Keeping comments on the why preserves the information the
code cannot carry without creating a second description that silently goes
stale.

### XVI. Contained Changes

A change MUST be limited to the context it was asked to address. Refactoring,
renaming, reformatting, or behaviour adjustments outside that context MUST NOT
ride along; each belongs to its own change. This principle governs the scope of
a change as a whole; Principle VII governs how that change is divided into
commits, and a change that stays within scope MAY still span several commits.

**Rationale:** a change that reaches beyond its stated scope is a change nobody
reviewed on purpose. It hides the intended fix inside unrelated edits, makes
the diff expensive to read, and turns a revert into a choice between losing the
fix and keeping an unrelated regression.

## Technology Stack and Constraints

- Language and runtime: Python 3.8 in CI and `pyproject.toml` (`^3.8`); the
  production image (`docker/Dockerfile`) builds on Python 3.9. Dependencies
  are managed with Poetry (`pyproject.toml`, `poetry.lock`).
- Framework: Django 4.0 with Django REST Framework for REST, Django Channels for
  WebSockets, Celery for asynchronous tasks.
- Data stores: PostgreSQL as the primary database, Redis for channel layers and
  cache.
- Layout: domain apps under `chats/apps/<app>/`; HTTP and WebSocket interfaces
  under `chats/apps/api/` (`v1`, `v2`, `websockets`); event-driven consumers
  under `chats/apps/event_driven/`.
- Timestamps MUST use `django.utils.timezone` (or `datetime.utcnow()`);
  `datetime.now()` is blocked by the `check-datetime-now` hook.

## Development Workflow and Quality Gates

- Pre-commit hooks defined in `.pre-commit-config.yaml` MUST pass, and secret
  detection hooks MUST never be skipped.
- CI runs migrations, `flake8`, `black`, `isort`, and the Django test suite
  (`manage.py test`) with coverage; the run MUST be green before merge.
- Every plan produced by `/speckit-plan` MUST include a Constitution Check
  against the principles above; violations MUST be justified in the plan's
  complexity tracking or removed.

## Governance

This constitution supersedes other engineering practices for this repository.
Root engineering principles (I–VIII) prevail over backend principles (IX–XVI),
which prevail over project-specific adaptations; an exception MUST be stated
explicitly in the affected principle with its justification.

Amendments MUST be made through a pull request that updates this file, the Sync
Impact Report, and the version line. Versioning follows SemVer: MAJOR when a
principle is removed or redefined incompatibly, MINOR when a principle or
section is added or materially expanded, PATCH for clarifications and wording.
Upstream changes in `weni-ai/vtex-cx-engineering-constitutions` SHOULD be
re-synced through `setup-engineering`.

Every pull request review MUST verify compliance. `/speckit-analyze` MUST treat
any conflict with a `MUST` in this document as CRITICAL.

**Version**: 1.0.0 | **Ratified**: 2026-10-01 | **Last Amended**: 2026-10-01
