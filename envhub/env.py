"""Build an Arena environment from a graph spec YAML for LeRobot (EnvHub entry point).

``make_env`` is the function LeRobot's EnvHub expects. It is reached through
:meth:`envhub.config.ArenaYamlEnv.create_envs` (``--env.type=arena_yaml``).

Isaac Sim is launched *inside* ``make_env``. Nothing at module level may import
``isaaclab``, because LeRobot imports this file while parsing CLI arguments.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import gymnasium as gym
import numpy as np

from .isaaclab_env_wrapper import IsaacLabEnvWrapper, close_simulation

if TYPE_CHECKING:
    from .config import ArenaYamlEnv

logger = logging.getLogger(__name__)


def make_env(
    n_envs: int = 1,
    use_async_envs: bool = False,
    cfg: ArenaYamlEnv | None = None,
) -> dict[str, dict[int, gym.vector.VectorEnv]]:
    """Launch Isaac Sim and return ``{spec env_name: {0: vector_env}}`` for LeRobot.

    Args:
        n_envs: Sub-environments batched inside the one simulation (``--eval.batch_size``).
        use_async_envs: Ignored — Isaac Lab always batches on the GPU inside one process.
            LeRobot's ``--eval.use_async_envs`` defaults to True, so this is expected to
            be set on most runs; it just doesn't mean anything for Isaac Lab.
        cfg: The :class:`envhub.config.ArenaYamlEnv` LeRobot built from the CLI.
    """
    assert cfg is not None, "make_env needs an env config (pass --env.type=arena_yaml)"
    assert cfg.spec, "pass --env.spec=<path to a task YAML under environments/>"
    assert n_envs >= 1, f"n_envs must be at least 1, got {n_envs}"
    if use_async_envs:
        logger.info(
            "Ignoring --eval.use_async_envs=True: Isaac Lab batches environments inside a single "
            "simulation process regardless of this flag. Scale with --eval.batch_size instead."
        )

    state_keys = _split_keys(cfg.state_keys)
    camera_keys = _split_keys(cfg.camera_keys)
    assert not camera_keys or cfg.enable_cameras, "--env.camera_keys requires --env.enable_cameras=true"

    spec_path = _resolve_spec_path(cfg.spec)
    simulation_app = _launch_simulation_app(cfg)
    env = None
    try:
        env, env_name = _build_isaaclab_env(cfg, spec_path, n_envs)
        _apply_observation_layout(env, cfg, state_keys, camera_keys)
        wrapped = IsaacLabEnvWrapper(
            env,
            episode_length=cfg.episode_length or int(env.unwrapped.max_episode_length),
            task=env.unwrapped.get_language_instruction(),
            simulation_app=simulation_app,
        )
    except Exception:
        # Kit's app.close() (inside close_simulation) can hard-kill the process with exit
        # code 0 before Python gets to print a traceback, silently swallowing the real
        # error. Log it first, and flush so it survives that.
        logger.exception("Failed to build the Isaac Lab Arena environment")
        sys.stdout.flush()
        sys.stderr.flush()
        close_simulation(env, simulation_app)
        raise
    logger.info("Built %s with %d env(s), task=%r", env_name, wrapped.num_envs, wrapped.task)
    return {env_name: {0: wrapped}}


def _split_keys(keys: str | None) -> tuple[str, ...]:
    """Split a comma-separated CLI list such as ``--env.camera_keys=cam_a,cam_b``."""
    return tuple(key.strip() for key in (keys or "").split(",") if key.strip())


def _resolve_spec_path(spec: str) -> Path:
    """Resolve ``--env.spec`` against ``ARENA_PROJECT_ROOT``, so eval runs from anywhere."""
    path = Path(spec).expanduser()
    if not path.is_absolute():
        path = Path(os.environ.get("ARENA_PROJECT_ROOT", ".")) / path
    assert path.is_file(), f"--env.spec={spec} not found (looked for {path})"
    return path


def _launch_simulation_app(cfg: ArenaYamlEnv) -> Any:
    """Start Isaac Sim. Every ``isaaclab*`` import has to happen after this."""
    if cfg.enable_pinocchio:
        # Pinocchio (Pink IK embodiments) must be imported before Isaac Sim to avoid a symbol clash.
        import pinocchio  # noqa: F401

    from isaaclab.app import AppLauncher

    launcher_args: dict[str, Any] = {
        "headless": cfg.headless,
        "enable_cameras": cfg.enable_cameras,
        "device": cfg.device,
    }
    # Isaac Lab 3.0 selects GUI/visualizer backends with --viz; omitting it means headless.
    if cfg.visualizer:
        launcher_args["visualizer"] = cfg.visualizer
    return AppLauncher(launcher_args)


def _build_isaaclab_env(cfg: ArenaYamlEnv, spec_path: Path, n_envs: int) -> tuple[Any, str]:
    """Compose the spec into a batched Isaac Lab env, returned with the spec's ``env_name``."""
    from isaaclab_arena.environment_spec.arena_env_graph_spec import ArenaEnvGraphSpec
    from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder
    from isaaclab_arena.environments.arena_env_builder_cfg import ArenaEnvBuilderCfg

    spec = ArenaEnvGraphSpec.from_yaml(spec_path)
    logger.info("Loaded %s from %s: %s", spec.env_name, spec_path, spec.summary())
    # Cameras are spawned by the embodiment, so the flag has to reach it here.
    arena_env = spec.to_arena_env(enable_cameras=cfg.enable_cameras)

    builder_cfg = ArenaEnvBuilderCfg(
        num_envs=n_envs,
        device=cfg.device or "cuda:0",
        seed=cfg.seed if cfg.seed is not None else 0,
        disable_fabric=cfg.disable_fabric,
        mimic=cfg.mimic,
        language_instruction=cfg.task,
    )
    builder = ArenaEnvBuilder(arena_env, builder_cfg)
    env_cfg, env_kwargs = builder.compose_manager_cfg()
    # IsaaclabArenaProcessorStep indexes obs["policy"] by term name, which a
    # concatenating embodiment would collapse into one unnamed tensor.
    env_cfg.observations.policy.concatenate_terms = False
    # rgb_array lets LeRobot grab viewport frames for its evaluation videos.
    render_mode = "rgb_array" if cfg.enable_cameras else None
    env = builder.make_registered(env_cfg=env_cfg, env_kwargs=env_kwargs, render_mode=render_mode)
    return env, spec.env_name


def _apply_observation_layout(
    env,
    cfg: ArenaYamlEnv,
    state_keys: tuple[str, ...],
    camera_keys: tuple[str, ...],
) -> None:
    """Check the requested keys and measure the dimensions they imply off the built env.

    LeRobot's processor silently skips a ``state_key`` it cannot find, so a typo would
    otherwise surface only as a short state vector. Taking the dimensions from the
    environment rather than from ``--env.state_dim``/``--env.action_dim`` keeps the
    policy features honest for any spec, whatever robot and cameras it names.
    """
    observations = env.unwrapped.observation_manager
    state_terms = observations.active_terms.get("policy", [])
    camera_terms = observations.active_terms.get("camera_obs", [])

    unknown = [key for key in state_keys if key not in state_terms]
    assert not unknown, f"--env.state_keys {unknown} are not in the policy group {sorted(state_terms)}"
    unknown = [key for key in camera_keys if key not in camera_terms]
    assert not unknown, f"--env.camera_keys {unknown} are not in the camera group {sorted(camera_terms)}"

    # group_obs_dim may be a single concatenated shape; group_obs_term_dim is always per-term.
    term_dims = dict(zip(state_terms, observations.group_obs_term_dim.get("policy", []), strict=True))
    cfg.state_dim = sum(int(np.prod(term_dims[key])) for key in state_keys)
    cfg.action_dim = int(env.action_space.shape[-1])

    if camera_keys:
        camera_dims = dict(zip(camera_terms, observations.group_obs_term_dim.get("camera_obs", []), strict=True))
        resolutions = {tuple(camera_dims[key][:2]) for key in camera_keys}
        assert len(resolutions) == 1, (
            f"--env.camera_keys {list(camera_keys)} render at different resolutions "
            f"({sorted(resolutions)}); LeRobot describes them all with one camera_height/width"
        )
        height, width = resolutions.pop()
        cfg.camera_height, cfg.camera_width = int(height), int(width)

    # Rebuild the PolicyFeature entries that __post_init__ derived from the old numbers.
    cfg.__post_init__()
    logger.info(
        "Observation layout: state=%s (%d), action=%d, cameras=%s (%dx%d)",
        list(state_keys),
        cfg.state_dim,
        cfg.action_dim,
        list(camera_keys),
        cfg.camera_height,
        cfg.camera_width,
    )
