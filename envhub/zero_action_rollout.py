"""Smoke-test the EnvHub wiring: build a spec and step zero actions, no policy involved.

    python -m envhub.zero_action_rollout \
        --env.type=arena_yaml \
        --env.spec=environments/tasks/banana_in_bowl.yaml \
        --eval.batch_size=1 \
        --env.visualizer=kit

Prints the observation terms the robot publishes, which is where the names for
``--env.state_keys`` and ``--env.camera_keys`` come from.
"""

import logging
from pprint import pformat

import torch
import tqdm
from lerobot.configs import parser
from lerobot.configs.eval import EvalPipelineConfig
from lerobot.envs.factory import make_env


@parser.wrap()
def main(cfg: EvalPipelineConfig):
    logging.info(pformat(cfg.env))

    env = next(iter(make_env(cfg.env, n_envs=cfg.eval.batch_size).values()))[0]
    try:
        obs, _ = env.reset()
        print(f"state terms: {list(obs['policy'])}")
        print(f"camera terms: {list(obs.get('camera_obs', {}))}")
        print(f"task: {env.task!r}, max steps: {env.call('_max_episode_steps')[0]}")
        # Measured off the built env by envhub.env, not taken from the CLI.
        print(
            f"selected: state {cfg.env.state_keys} -> {cfg.env.state_dim}, action {cfg.env.action_dim}, "
            f"cameras {cfg.env.camera_keys} at {cfg.env.camera_height}x{cfg.env.camera_width}"
        )

        actions = torch.zeros((env.num_envs, env.action_space.shape[-1]), device=env.device)
        for _ in tqdm.tqdm(range(100), desc="zero actions"):
            with torch.inference_mode():
                env.step(actions)
    finally:
        env.close()


if __name__ == "__main__":
    main()
