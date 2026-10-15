# Selected FULLPAGE-V5 runtime bundle

This local bundle records the selected TRAIN-025 checkpoint and its development output. The canonical checkpoint and output remain in their original project paths.

## Selection

- Run: `TRAIN-025`, step `1800`
- Selection report: `reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json`
- Checkpoint pointer: `checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt`
- Local model pointer: `training/selected/fullpage-v5/model/TRAIN-025-step1800.pt`
- Local development output: `training/selected/fullpage-v5/development-output/`
- Development scope: 80 of 80 accepted requests, `final_used=false`
- Checkpoint SHA-256: `c1a450149eb8f860cc42595bba283e0f9e915a436f38f967516bc5107bd1c446`
- Selection report SHA-256: `f637c04e80f01d55ff6b37d6b0f2e6b1434a50da572597fd57a80b32bb83f512`
- Development request-set SHA-256: `e4878282587164116459f1de23a62fb53ba8be1b4866a48166491181e1f25173`
- Development request-file SHA-256: `2091d047ee3692dcba1fbdb9b81e4c20e56b85e1ff46ad54b5eacd906c9d6836`
- Development identity SHA-256: `4cd88d9a29d9f1826ae5beeb87a62ada6f01b5c61684bdb3fe3816b3dda47d1a`
- Browser review: pending
- Human visual review: pending

The selected report and checkpoint identity are bound by the SHA-256 values in `selection.json`. The checkpoint pointer, its `.versions` payload, and payload manifest are copied together so the local pointer remains valid.

## Local-only copies

The `model/` and `development-output/` directories are ignored by Git. Keep them on this machine and do not commit or upload them. The tracked `selection.json` contains provenance metadata, not model weights or generated pages.

Training code remains under `src/`, canonical checkpoints remain under `checkpoints/`, and the canonical development output remains under `outputs/fullpage/FULLPAGE-V5/TRAIN-025-step1800`.

## Evaluation limits

The bundle passed the frozen development selection gate. Browser inspection and human visual review have not been completed. This result does not establish 95 percent visual quality or production readiness.

## Application integration

The approved local application plan uses this package from the FastAPI adapter in `apps/api`, with a chat interface in `apps/web`. Read the [application design](../../../docs/superpowers/specs/2026-10-15-generator-chat-application-design.md) and [implementation roadmap](../../../docs/superpowers/plans/2026-10-15-generator-app-roadmap.md) for the integration boundary and current implementation order.
