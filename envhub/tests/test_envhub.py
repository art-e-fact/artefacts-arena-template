"""Checks that do not need Isaac Sim. Run with ``pytest envhub``."""

import json
import sys

import pytest

from envhub.env import _resolve_spec_path, _split_keys


def test_plugin_discovery_registers_without_importing_isaaclab():
    """LeRobot imports this package while parsing CLI args, before Isaac Sim exists."""
    from lerobot.configs.parser import load_plugin
    from lerobot.envs.configs import EnvConfig

    load_plugin("envhub")

    assert "arena_yaml" in EnvConfig.get_known_choices()
    assert not [m for m in sys.modules if m.split(".")[0] in ("isaaclab", "isaaclab_arena", "isaacsim")]


def test_split_keys():
    assert _split_keys(" joint_pos , gripper_pos ,") == ("joint_pos", "gripper_pos")
    assert _split_keys(None) == ()


def test_resolve_spec_path(monkeypatch, tmp_path):
    spec = tmp_path / "environments" / "tasks" / "a.yaml"
    spec.parent.mkdir(parents=True)
    spec.touch()
    monkeypatch.setenv("ARENA_PROJECT_ROOT", str(tmp_path))

    assert _resolve_spec_path("environments/tasks/a.yaml") == spec
    assert _resolve_spec_path(str(spec)) == spec
    with pytest.raises(AssertionError, match="not found"):
        _resolve_spec_path("environments/tasks/missing.yaml")


def test_add_openpi_stats_writes_sliced_stats(tmp_path):
    """openpi keeps 32-wide padded stats; the policy sees the first state_dim / action_dim."""
    from safetensors import safe_open

    from envhub.add_openpi_stats import write_checkpoint

    src = tmp_path / "src"
    src.mkdir()
    (src / "config.json").write_text("{}")
    (src / "model.safetensors").write_bytes(b"")
    steps = [{"registry_name": "to_batch_processor", "config": {}}, {"registry_name": None, "config": {}}]
    (src / "policy_preprocessor.json").write_text(json.dumps({"steps": steps + [{"registry_name": "normalizer_processor", "config": {"features": {}}}]}))
    (src / "policy_postprocessor.json").write_text(json.dumps({"steps": [{"registry_name": "unnormalizer_processor", "config": {"features": {}}}]}))
    norm_stats = {name: {stat: list(range(32)) for stat in ("mean", "std", "q01", "q99")} for name in ("state", "actions")}

    write_checkpoint(src, tmp_path / "out", norm_stats, state_dim=8, action_dim=7)

    pre = json.loads((tmp_path / "out" / "policy_preprocessor.json").read_text())["steps"][2]
    assert pre["state_file"] == "policy_preprocessor_step_2_normalizer_processor.safetensors"
    assert pre["config"]["features"] == {
        "observation.state": {"type": "STATE", "shape": [8]},
        "action": {"type": "ACTION", "shape": [7]},
    }
    with safe_open(tmp_path / "out" / pre["state_file"], framework="pt") as f:
        assert f.get_tensor("observation.state.q01").tolist() == list(range(8))
        assert f.get_tensor("action.q99").tolist() == list(range(7))
    post = json.loads((tmp_path / "out" / "policy_postprocessor.json").read_text())["steps"][0]
    with safe_open(tmp_path / "out" / post["state_file"], framework="pt") as f:
        assert sorted(f.keys()) == ["action.mean", "action.q01", "action.q99", "action.std"]
