"""LeRobot EnvHub packaging for this project's Arena environment specs.

Importing this package registers the ``arena_yaml`` env type with LeRobot, so the
stock LeRobot CLI builds any spec under ``environments/`` without a wrapper script:

    lerobot-eval --env.discover_packages_path=envhub --env.type=arena_yaml \
                 --env.spec=environments/tasks/banana_in_bowl.yaml ...

Nothing in this package may import ``isaaclab`` at module level: LeRobot imports
the package (and every submodule) while parsing CLI arguments, long before Isaac
Sim is launched.
"""

from .config import ArenaYamlEnv
from .env import make_env

__all__ = ["ArenaYamlEnv", "make_env"]
