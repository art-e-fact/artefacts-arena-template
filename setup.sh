#!/usr/bin/env bash
# Host (non-Docker) environment for this Arena project.
#
# Syncs IsaacLab-Arena's uv venv (Isaac Lab + Arena), installs this repo's
# packages and LeRobot into it, then activates that venv in the current shell.
#
# Must be sourced so activation sticks:
#   source ./setup.sh
#   # or: . ./setup.sh
#
# Options (pass after sourcing, e.g. `source ./setup.sh --wheel`):
#   --wheel   Use Arena's isaaclab-from-wheel group instead of from-source
#   --force   Re-run uv sync even if the venv already exists
#   -h/--help Show this help
#
# Requires uv (https://docs.astral.sh/uv/), a Rust toolchain (arena_composer is
# a maturin project — the Bevy viewer is compiled on install, which takes a few
# minutes the first time), and the Arena submodule:
#   git submodule update --init --recursive

_setup_main() {
  local REPO_ROOT ARENA_DIR VENV_DIR FORCE=false WHEEL=false
  local UV_SYNC_ARGS=()

  # Resolve repo root whether sourced or executed.
  if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  else
    REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
  fi
  ARENA_DIR="${REPO_ROOT}/submodules/IsaacLab-Arena"
  VENV_DIR="${ARENA_DIR}/.venv"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --wheel) WHEEL=true ;;
      --force) FORCE=true ;;
      -h|--help)
        sed -n '2,19p' "${BASH_SOURCE[0]:-$0}" | sed 's/^# \?//'
        return 0
        ;;
      *)
        echo "setup.sh: unknown option: $1 (try --help)" >&2
        return 2
        ;;
    esac
    shift
  done

  if [[ ! -f "${ARENA_DIR}/pyproject.toml" ]]; then
    echo "setup.sh: Arena submodule missing at ${ARENA_DIR}" >&2
    echo "  Run: git submodule update --init --recursive" >&2
    return 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "setup.sh: uv not found on PATH. Install: https://docs.astral.sh/uv/" >&2
    return 1
  fi

  if ! command -v cargo >/dev/null 2>&1; then
    echo "setup.sh: cargo not found on PATH. Install: https://rustup.rs/" >&2
    return 1
  fi

  if [[ "${WHEEL}" == true ]]; then
    UV_SYNC_ARGS=(--no-default-groups --group isaaclab-from-wheel)
  fi

  # Sync on first use, when --force, or when switching to the wheel flavor.
  if [[ "${FORCE}" == true || "${WHEEL}" == true || ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "setup.sh: syncing Arena environment in ${ARENA_DIR} ..."
    (cd "${ARENA_DIR}" && uv sync "${UV_SYNC_ARGS[@]}") || return 1
  else
    echo "setup.sh: Arena venv already present (pass --force to re-sync)"
  fi

  # uv venvs do not ship pip; install into Arena's env with uv pip.
  # This compiles the Bevy viewer (see arena_composer/Cargo.toml) — minutes on
  # a cold cargo cache, seconds afterwards.
  if [[ -f "${REPO_ROOT}/arena_composer/pyproject.toml" ]]; then
    echo "setup.sh: installing arena_composer (editable, builds the viewer) ..."
    uv pip install --python "${VENV_DIR}/bin/python" \
      -e "${REPO_ROOT}/arena_composer" || return 1
  else
    echo "setup.sh: no arena_composer/pyproject.toml — skipping project install"
  fi

  # LeRobot, to train and evaluate policies in these environments (see envhub/).
  # transformers 5 has to be asked for directly: LeRobot needs huggingface-hub>=1
  # and transformers 4 caps it below that. The overrides hold numpy and packaging
  # at the exact versions isaacsim-kernel requires; LeRobot's own bounds would
  # move both and break Isaac Sim.
  echo "setup.sh: installing LeRobot ..."
  uv pip install --python "${VENV_DIR}/bin/python" \
    --overrides <(printf '%s\n' 'numpy==2.3.1' 'packaging==26.0') \
    lerobot[dataset,smolvla,pi] 'transformers>=5.4.0,<5.6.0' || return 1

  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate" || return 1

  export OMNI_KIT_ACCEPT_EULA=YES
  export ACCEPT_EULA=Y
  export ARENA_PROJECT_ROOT="${REPO_ROOT}"
  # Console scripts do not put cwd on sys.path, so repo-root packages are not
  # importable from them unless the repo root is on PYTHONPATH.
  case ":${PYTHONPATH:-}:" in
    *":${REPO_ROOT}:"*) ;;
    *) export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" ;;
  esac

  cd "${REPO_ROOT}" || return 1

  echo "setup.sh: ready — python=$(command -v python)"
}

# Refuse bare execution: activation must apply to the caller's shell.
if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
  echo "setup.sh: source this script instead of executing it:" >&2
  echo "  source ./setup.sh" >&2
  exit 1
fi

_setup_main "$@"
_setup_rc=$?
unset -f _setup_main
return "${_setup_rc}"
