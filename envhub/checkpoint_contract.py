"""Print what a LeRobot checkpoint expects of an environment.

    python -m envhub.checkpoint_contract lerobot/pi05_droid
    python -m envhub.checkpoint_contract outputs/checkpoints/pi05_droid

A checkpoint carries its contract in two places. ``config.json`` names the feature keys
and the normalization kind per feature type; the ``*_normalizer_processor.safetensors``
files hold the per-key stats. Only the stats bind at eval time: a state or action of
another width than its stats fails inside the normalizer, a key with no stats is passed
through untouched, and the shapes in ``config.json`` are never checked. Compare the stats
widths with the ``selected: state ... action ...`` line ``envhub.zero_action_rollout``
prints for the environment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files
from safetensors import safe_open


def checkpoint_dir(checkpoint: str) -> Path:
    """A local directory as is; a Hub id fetched without its weights."""
    if Path(checkpoint).is_dir():
        return Path(checkpoint)
    names = [n for n in list_repo_files(checkpoint) if n.endswith(".json") or "normalizer_processor" in n]
    assert "config.json" in names, f"{checkpoint} has no config.json: not a LeRobot checkpoint"
    paths = [hf_hub_download(checkpoint, name) for name in names]
    return Path(paths[0]).parent


def main(checkpoint: str) -> None:
    root = checkpoint_dir(checkpoint)
    config = json.loads((root / "config.json").read_text())
    # Absent keys take the policy class defaults when LeRobot loads the config.
    print("normalization:", config.get("normalization_mapping", "(policy default)"))
    for name in ("input_features", "output_features"):
        print(f"{name}:", {key: tuple(ft["shape"]) for key, ft in config[name].items()})

    for pipeline in ("policy_preprocessor", "policy_postprocessor"):
        path = root / f"{pipeline}.json"
        if not path.is_file():
            continue
        print(f"\n{pipeline}:")
        for i, step in enumerate(json.loads(path.read_text())["steps"]):
            config = {k: v for k, v in step.get("config", {}).items() if k not in ("features", "norm_map", "stats")}
            print(f"  {i} {step.get('registry_name')} {config or ''}")
            if "normalizer" not in (step.get("registry_name") or ""):
                continue
            if not step.get("state_file"):
                print("      no stats: every key is passed through unnormalized")
                continue
            with safe_open(root / step["state_file"], framework="pt") as stats:
                widths = {}
                for flat_key in stats.keys():
                    key, stat = flat_key.rsplit(".", 1)
                    widths.setdefault(key, {})[stat] = tuple(stats.get_tensor(flat_key).shape)
            for key, stat_shapes in sorted(widths.items()):
                shape = stat_shapes.get("mean") or next(iter(stat_shapes.values()))
                print(f"      {key:36s} {shape}  {sorted(stat_shapes)}")


if __name__ == "__main__":
    main(sys.argv[1])
