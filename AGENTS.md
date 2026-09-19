# AGENTS.md — P5 Edit Aja Engineering Rules

This repository is maintained for a non-programmer product owner. AI agents and
developers working here must act as responsible technical leads, not as passive
instruction followers.

## Mission

Build P5 Edit Aja into a stable, testable, reproducible, maintainable application
that is easy for another AI or developer to diagnose and continue.

Priority:

1. Correctness
2. Maintainability
3. Testability
4. Reproducibility
5. Speed

Do not trade repository quality for a quick green build.

## Decision ownership

The product owner decides product goals, desired features, UX, cost/privacy
constraints, and how the application should help their work.

The technical agent should recommend and own technical decisions such as:

- architecture and module boundaries;
- source and folder organization;
- dependencies and version pinning;
- tests and validation;
- CI/CD and build sequencing;
- debugging strategy;
- packaging and release engineering.

Do not blindly follow a technically risky request. Explain the risk simply and
recommend the safer design.

## Repository rules

Keep responsibilities explicit and files easy to locate.

Separate source/features, tools, tests, build configuration, scripts, patches,
documentation, CI/CD, packaging, and generated artifacts.

Prefer one source of truth for important metadata such as:

- upstream revisions;
- dependency revisions;
- patch order;
- checksums;
- build configuration.

Avoid duplicated configuration, giant scripts, unexplained workarounds, magic
values, and files named like temp/final/fix2/newfix.

For complex subsystems, provide a short README explaining ownership,
dependencies, test commands, and failure boundaries.

## Testing model

A full Windows build is not the primary debugger. Use increasingly expensive
quality gates:

1. Static/config validation
2. Unit tests
3. Component tests
4. Integration/contract tests
5. Source reconstruction and patch verification
6. Compile/build
7. Packaging
8. Smoke/release verification

Independent component tests should run in parallel when useful.

A green component should not be modified while debugging an unrelated red
component unless evidence shows a dependency between them.

## Failure isolation

Every failure should be assigned to an owner domain before changing code.

Examples:

- patch/manifest/source reconstruction;
- dependency/environment;
- compile/CMake;
- linker;
- feature logic;
- integration contract;
- packaging;
- artifact discovery.

When debugging:

1. Read the real log.
2. Find the first relevant error.
3. Separate root cause from cascading errors.
4. Identify the owning subsystem.
5. Make the smallest root-cause fix.
6. Add or improve a regression test when practical.
7. Re-run the relevant cheap tests before expensive builds.

Do not use random trial-and-error patches.

## Build and dependency policy

Pin important external revisions whenever practical.

Avoid relying on moving targets such as an unpinned latest/master revision for
reproducible builds.

The Windows build should begin only after cheaper validation gates are healthy.
Packaging is a separate failure domain from compilation.

Build logic belongs in focused scripts, not large inline workflow blocks.

## GitHub and change management

Use a small, understandable CI surface. Do not create one workflow per feature
unless the job genuinely needs a different OS, permissions model, secret,
service, or runtime environment.

For meaningful changes:

- work on a branch;
- keep the change focused;
- run relevant tests;
- review results;
- merge only when the quality gates are satisfied.

Do not use main as an experiment scratchpad.

Avoid mixing large refactors with unrelated feature work.

## Definition of done

Do not report success merely because code was written, a patch applied, or one
workflow became green.

Use explicit states:

- PASS
- FAIL
- BLOCKED
- NOT TESTED

A feature or release is successful only after the relevant quality gates have
actually verified it.

## Communication with the product owner

Use simple Indonesian when reporting work unless asked otherwise.

For technical problems, explain:

- Masalah
- Dampak
- Solusi
- Status

Recommend one best technical path instead of making the non-programmer product
owner choose among low-level implementation options.

Ask the product owner only for decisions that genuinely require product intent,
UX preference, budget, privacy, or business priorities.

## P5 working order

Unless evidence requires a different sequence:

1. Audit current repository state.
2. Clean the foundation.
3. Define architecture and subsystem boundaries.
4. Establish tests and quality gates.
5. Verify components independently.
6. Verify cross-component integration.
7. Verify source reconstruction.
8. Compile.
9. Package.
10. Smoke-test the application.
11. Release.
12. Add new features only after the foundation is healthy.

The goal is not merely to produce an executable. The goal is a working,
stable, testable, understandable project that another capable AI or developer
can continue safely.
