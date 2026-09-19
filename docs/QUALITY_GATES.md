# P5 quality gates

P5 Edit Aja uses layered verification so a full Windows build is the final
expensive check, not the first debugging tool.

## Gate order

1. **Static / Repository** — Python syntax, JSON examples, repository layout.
2. **Component tests** — independent feature domains run in parallel.
3. **Contracts / Examples** — CLI contracts and representative example flows.
4. **Build / Configuration** — pinned revisions, checksums, workflow YAML,
   Python build helpers, and PowerShell syntax.
5. **Source / Reconstruction** — reconstruct the pinned Kdenlive source on
   Linux and apply/verify the complete P5 patch chain.
6. **Windows compile** — only a successful `main` quality-gate run can trigger
   the Windows build, which checks out that exact verified commit.
7. **Packaging** — create and collect the Windows artifact.
8. **Release smoke test** — verify the packaged application starts and key
   product flows work.

## Component boundaries

| Gate | Typical ownership |
| --- | --- |
| AI Control | AI Edit, Local Edit, Film Context, capability registry, creator orchestration |
| Media Editorial | media analysis, dialogue, beats, montage, highlights, B-roll |
| Audio Speech | audio analysis, ducking, transcription and cleanup backends |
| Captions | caption generation, animation and speaker handling |
| Visual Segmentation | visual intelligence, SAM adapter and mask effects |
| Documentary | documentary toolkit, graphics and motion templates |
| Build / Configuration | manifest, pinned revisions, workflow syntax, build helpers |
| Source / Reconstruction | upstream source, patch order/application, branding, required source markers |

A green domain should remain untouched while repairing an unrelated red domain
unless failure evidence shows a dependency.

## Debugging rule

When a gate fails:

1. read the actual log;
2. identify the first relevant error;
3. assign the failure to one owner domain;
4. make the smallest root-cause fix;
5. add a regression test when practical;
6. rerun the cheap owning gate before an expensive Windows build.

Do not use repeated full builds as trial-and-error debugging.
