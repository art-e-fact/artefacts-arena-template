"""Checks that do not need Isaac Sim. Run with ``pytest envhub``."""

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
