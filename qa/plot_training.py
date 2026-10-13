"""Export baseline loss and learning-rate curves from actual step metrics."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    training, validation = {}, {}
    for run in ("TRAIN-003", "TRAIN-004"):
        with (ROOT / f"outputs/metrics/{run}.jsonl").open() as handle:
            for line in handle:
                row = json.loads(line)
                if row["event"] == "train":
                    training[row["step"]] = row
                elif row["event"] == "validation":
                    validation[row["step"]] = row
    steps = sorted(training)
    losses = [training[step]["loss"] for step in steps]
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    axes[0].plot(steps, losses, color="#2563eb", alpha=0.25, linewidth=0.6, label="Train loss per update")
    if len(steps) >= 20:
        axes[0].plot(steps[19:], np.convolve(losses, np.ones(20) / 20, mode="valid"), color="#2563eb", label="Train mean, 20 updates")
    val_steps = sorted(validation)
    axes[0].plot(val_steps, [validation[s]["loss"] for s in val_steps], color="#f97316", marker="o", markersize=4, label="Validation, fixed 128-block subset")
    axes[0].set_ylabel("Next-token cross entropy")
    axes[0].legend(frameon=False)
    axes[0].set_title("Mini GPT 14.19M | BF16 | 1,200 updates including checkpoint resume")
    axes[1].plot(steps, [training[s]["learning_rate"] for s in steps], color="#7c3aed")
    axes[1].set_ylabel("Learning rate")
    axes[1].set_xlabel("Optimizer update")
    axes[1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    for axis in axes:
        axis.grid(alpha=0.18)
        axis.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = ROOT / "reports/training/BASELINE_LOSS_2026-10-12.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print(json.dumps({"path": str(path), "train_updates": len(steps), "validation_points": len(val_steps)}))


if __name__ == "__main__":
    main()
