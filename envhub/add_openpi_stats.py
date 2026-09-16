"""Give an openpi-ported LeRobot checkpoint the normalization stats it was trained with.

LeRobot's ports of openpi checkpoints (``lerobot/pi05_droid``, ...) ship their normalizer
steps empty. LeRobot passes a key with no stats through untouched, so ``lerobot-eval`` would
hand the policy raw joint angles and execute its [-1, 1] outputs as-is. openpi publishes the
stats the weights were trained with; this writes them into a local copy of the checkpoint
for ``--policy.path``::

    python -m envhub.add_openpi_stats lerobot/pi05_droid \\
        https://storage.googleapis.com/openpi-assets/checkpoints/pi05_droid/assets/droid/norm_stats.json \\
        --out outputs/checkpoints/pi05_droid

openpi pads state and action to 32 and keeps stats for every entry; the policy only ever
sees the first ``state_dim`` / ``action_dim`` of them, sliced here the way openpi slices.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from safetensors.torch import save_file

STATS = ("mean", "std", "q01", "q99")
FEATURES = {"observation.state": ("state", "STATE"), "action": ("actions", "ACTION")}


def stats_tensors(norm_stats: dict, dims: dict[str, int]) -> dict[str, torch.Tensor]:
    """Flatten openpi's ``{state|actions: {stat: [32 floats]}}`` into LeRobot's ``key.stat`` tensors."""
    return {
        f"{key}.{stat}": torch.tensor(norm_stats[FEATURES[key][0]][stat][:dim], dtype=torch.float32)
        for key, dim in dims.items()
        for stat in STATS
    }


def write_checkpoint(src: Path, out: Path, norm_stats: dict, state_dim: int, action_dim: int) -> None:
    """Copy ``src`` to ``out`` with stats attached to its normalizer and unnormalizer steps."""
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "config.json", out / "config.json")
    if not (out / "model.safetensors").exists():
        os.symlink((src / "model.safetensors").resolve(), out / "model.safetensors")

    # The unnormalizer only ever sees actions; the normalizer also sees the state.
    for pipeline, step_name, keys in (
        ("policy_preprocessor", "normalizer_processor", ("observation.state", "action")),
        ("policy_postprocessor", "unnormalizer_processor", ("action",)),
    ):
        config = json.loads((src / f"{pipeline}.json").read_text())
        (index, step), = [(i, s) for i, s in enumerate(config["steps"]) if s["registry_name"] == step_name]
        dims = {"observation.state": state_dim, "action": action_dim}
        step["config"]["features"] = {k: {"type": FEATURES[k][1], "shape": [dims[k]]} for k in keys}
        step["state_file"] = f"{pipeline}_step_{index}_{step_name}.safetensors"
        save_file(stats_tensors(norm_stats, {k: dims[k] for k in keys}), out / step["state_file"])
        (out / f"{pipeline}.json").write_text(json.dumps(config, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_id", help="LeRobot checkpoint on the Hub, e.g. lerobot/pi05_droid")
    parser.add_argument("norm_stats", help="URL or path of openpi's norm_stats.json for that checkpoint")
    parser.add_argument("--out", type=Path, required=True, help="directory to write; pass it to --policy.path")
    parser.add_argument("--state_dim", type=int, default=8, help="DROID: 7 joints + gripper")
    parser.add_argument("--action_dim", type=int, default=8, help="DROID: 7 joints + gripper")
    args = parser.parse_args()

    if args.norm_stats.startswith(("http://", "https://")):
        with urllib.request.urlopen(args.norm_stats) as response:
            norm_stats = json.load(response)["norm_stats"]
    else:
        norm_stats = json.loads(Path(args.norm_stats).read_text())["norm_stats"]
    src = Path(snapshot_download(args.repo_id))
    write_checkpoint(src, args.out, norm_stats, args.state_dim, args.action_dim)
    print(f"wrote {args.out}: --policy.path={args.out}")


if __name__ == "__main__":
    main()
