"""The ``arena_yaml`` LeRobot env type: one env config for every spec in this project.

Subclasses LeRobot's ``IsaaclabArenaEnv``, which already turns Arena observations into
policy inputs (``IsaaclabArenaProcessorStep``: the ``state_keys`` terms concatenated
into ``observation.state``, one ``observation.images.<key>`` per camera key). Two
things change here: the environment comes from a graph spec YAML instead of a
registered example environment, and ``hub_path`` is cleared so
``lerobot.envs.make_env`` builds it locally rather than downloading an ``env.py``
from the Hugging Face Hub.
"""

from __future__ import annotations

from dataclasses import dataclass

import gymnasium as gym
from lerobot.envs.configs import EnvConfig, IsaaclabArenaEnv

from .env import make_env


@EnvConfig.register_subclass("arena_yaml")
@dataclass
class ArenaYamlEnv(IsaaclabArenaEnv):
    """An Arena environment graph spec, selected with ``--env.spec``."""

    spec: str | None = None
    """Path to a task YAML; relative paths resolve against ``ARENA_PROJECT_ROOT``."""

    hub_path: str | None = None
    """Empty so ``make_env`` builds the env locally (no ``--trust_remote_code``)."""

    # Observation layout. The keys must name terms the embodiment publishes *and* match
    # the dataset the policy was trained on; a key that names neither is rejected at
    # build time, with the valid terms listed. The defaults are the DROID arm's.
    # ``state_dim``, ``action_dim``, ``camera_height`` and ``camera_width`` are inherited
    # but ignored: env.py measures them off the built environment.
    state_keys: str = "joint_pos,gripper_pos"
    camera_keys: str | None = "external_camera_rgb,wrist_camera_rgb"
    enable_cameras: bool = True

    episode_length: int | None = None
    """Max rollout steps; ``None`` uses the Arena task's own ``episode_length_s``."""
    task: str | None = None
    """Language instruction; ``None`` keeps the Arena task's own description."""
    visualizer: str | None = None
    """Isaac Lab ``--viz`` backend, e.g. ``kit`` to watch the rollout in a window."""
    enable_pinocchio: bool = False
    """Only Pink IK embodiments need Pinocchio, and it must load before Isaac Sim."""

    # The spec names the scene, the robot and the objects, so these select nothing.
    environment: str | None = None
    embodiment: str | None = None
    object: str | None = None

    def create_envs(self, n_envs: int, use_async_envs: bool = False) -> dict[str, dict[int, gym.vector.VectorEnv]]:
        """Build the environment locally (called by ``lerobot.envs.make_env``)."""
        return make_env(n_envs=n_envs, use_async_envs=use_async_envs, cfg=self)
