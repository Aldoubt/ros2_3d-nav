#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="${ROS2_WS_ROOT:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"
ROS_DISTRO_NAME="${ROS_DISTRO:-humble}"
USE_CLEAN=0
COLCON_ARGS=()

while (($#)); do
  case "$1" in
    --clean)
      USE_CLEAN=1
      shift
      ;;
    *)
      COLCON_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "${VIRTUAL_ENV:-}" ]] && declare -F deactivate >/dev/null 2>&1; then
  deactivate
fi

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/ros/${ROS_DISTRO_NAME}/bin:${HOME}/.local/bin:${HOME}/.npm-global/bin"
unset PYTHONPATH || true
unset CONDA_PREFIX || true
unset CONDA_DEFAULT_ENV || true
unset CONDA_SHLVL || true

# ROS setup scripts may read unset vars like AMENT_TRACE_SETUP_FILES.
set +u
source "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
set -u

if [[ "${USE_CLEAN}" -eq 1 ]]; then
  rm -rf "${WS_ROOT}/build" "${WS_ROOT}/install" "${WS_ROOT}/log"
  rm -rf "${WS_ROOT}/src/build" "${WS_ROOT}/src/install" "${WS_ROOT}/src/log"
fi

cd "${WS_ROOT}"

exec colcon build \
  "${COLCON_ARGS[@]}" \
  --cmake-args \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  -DPython3_EXECUTABLE=/usr/bin/python3
