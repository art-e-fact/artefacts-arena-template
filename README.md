# Isaac Lab Arena Template

Boilerplate for a new Isaac Lab Arena project.

Features:
 - One-liner project setup.
 - Agentic development workflow.
 - Live kit-less 3D environment editor. (No RTX GPU required)
 - GUI and MCP based environment authoring. (⏳ TODO)
 - Integrated LeRobot training and evaluation.
 - Aretefacts CI pipeline. (⏳ TODO)
 - Parametric asset generation skills. (⏳ TODO)

## To try out

```sh
source setup.sh
arena-view environments/tasks/banana_in_bowl.yaml
```

Train a policy on these environments and evaluate it, with the stock LeRobot CLI:
[docs/lerobot.md](docs/lerobot.md).
