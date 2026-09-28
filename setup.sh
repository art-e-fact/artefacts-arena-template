#!/usr/bin/env bash
# Host (non-Docker) environment for this Arena project.
#
# Syncs IsaacLab-Arena's uv venv (Isaac Lab, Arena, the GR00T policy client),
# installs arena-composer into it at the version pinned below, then activates
# that venv in the current shell.
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
# ARENA_COMPOSER_SRC=<checkout> installs that checkout of arena-composer
# editable instead of the pinned wheel, for working on the composer itself.
#
# Requires uv (https://docs.astral.sh/uv/), gh (https://cli.github.com/ — the
# wheel is a GitHub Release asset), the Arena submodule, and a Rust toolchain
# only with ARENA_COMPOSER_SRC:
#   git submodule update --init --recursive

_setup_main() {
  local REPO_ROOT ARENA_DIR VENV_DIR WHEEL_DIR FORCE=false WHEEL=false
  # The arena-composer release to install, from art-e-fact/arena-composer.
  # It moves together with the Arena submodule.
  local ARENA_COMPOSER_VERSION=0.2.0
  # gr00t-client: the Isaac-GR00T source plus pyzmq, pinned by Arena's lockfile,
  # which Gr00tRemoteClosedloopPolicy needs to reach a GR00T server.
  local UV_SYNC_ARGS=(--group gr00t-client)

  # Resolve repo root whether sourced or executed.
  if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  else
    REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
  fi
  ARENA_DIR="${REPO_ROOT}/submodules/IsaacLab-Arena"
  VENV_DIR="${ARENA_DIR}/.venv"
  WHEEL_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/arena-composer/wheels/v${ARENA_COMPOSER_VERSION}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --wheel) WHEEL=true ;;
      --force) FORCE=true ;;
      -h|--help)
        sed -n '2,23p' "${BASH_SOURCE[0]:-$0}" | sed 's/^# \?//'
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

  if [[ "${WHEEL}" == true ]]; then
    UV_SYNC_ARGS+=(--no-default-groups --group isaaclab-from-wheel)
  fi

  # Sync on first use, when --force, when switching to the wheel flavor, or when
  # the GR00T client is missing: any uv sync without that group removes it.
  if [[ "${FORCE}" == true || "${WHEEL}" == true || ! -x "${VENV_DIR}/bin/python" ]] ||
    ! "${VENV_DIR}/bin/python" -c 'import gr00t.policy.server_client' 2>/dev/null; then
    echo "setup.sh: syncing Arena environment in ${ARENA_DIR} ..."
    (cd "${ARENA_DIR}" && uv sync "${UV_SYNC_ARGS[@]}") || return 1
  else
    echo "setup.sh: Arena venv already present (pass --force to re-sync)"
  fi

  # arena-composer (arena-view, arena-mcp, ...) goes into Arena's venv with uv
  # pip, since uv venvs ship no pip. Arena's lockfile does not list it, so a
  # sync removes it: this runs after the sync, every time.
  if [[ -n "${ARENA_COMPOSER_SRC:-}" ]]; then
    # Cargo builds the viewer: minutes on a cold cache, seconds afterwards.
    if ! command -v cargo >/dev/null 2>&1; then
      echo "setup.sh: cargo not found on PATH; ARENA_COMPOSER_SRC needs it. Install: https://rustup.rs/" >&2
      return 1
    fi
    echo "setup.sh: installing arena-composer editable from ${ARENA_COMPOSER_SRC} ..."
    uv pip install --python "${VENV_DIR}/bin/python" -e "${ARENA_COMPOSER_SRC}" || return 1
  # Not installed, another version, or editable from an earlier
  # ARENA_COMPOSER_SRC run: install the pinned wheel.
  elif "${VENV_DIR}/bin/python" -c "
import importlib.metadata as m, json, sys
d = m.distribution('arena-composer')
editable = json.loads(d.read_text('direct_url.json') or '{}').get('dir_info', {}).get('editable', False)
sys.exit(d.version != '${ARENA_COMPOSER_VERSION}' or editable)" 2>/dev/null; then
    echo "setup.sh: arena-composer ${ARENA_COMPOSER_VERSION} already installed"
  else
    if ! command -v gh >/dev/null 2>&1; then
      echo "setup.sh: gh not found on PATH. Install: https://cli.github.com/" >&2
      return 1
    fi
    echo "setup.sh: installing arena-composer ${ARENA_COMPOSER_VERSION} ..."
    gh release download "v${ARENA_COMPOSER_VERSION}" -R art-e-fact/arena-composer \
      -p '*.whl' -D "${WHEEL_DIR}" --clobber || return 1
    uv pip install --python "${VENV_DIR}/bin/python" "${WHEEL_DIR}"/*.whl || return 1
  fi

  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate" || return 1

  export OMNI_KIT_ACCEPT_EULA=YES
  export ACCEPT_EULA=Y

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
