#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

APP_DIR="${1:-${ROS_QT5_GUI_APP_DIR:-}}"

if [[ -z "${APP_DIR}" ]]; then
  echo "Usage: $0 /path/to/Ros_Qt5_Gui_App"
  echo "   or: ROS_QT5_GUI_APP_DIR=/path/to/Ros_Qt5_Gui_App $0"
  exit 1
fi

if [[ ! -d "${APP_DIR}" ]]; then
  echo "Ros_Qt5_Gui_App directory not found: ${APP_DIR}" >&2
  exit 1
fi

source_if_exists() {
  local setup_file="$1"
  if [[ -f "${setup_file}" ]]; then
    set +u
    # shellcheck disable=SC1090
    source "${setup_file}"
    set -u
  fi
}

source_if_exists /opt/ros/humble/setup.bash
source_if_exists "${WS_ROOT}/install/setup.bash"

if [[ -x "${APP_DIR}/build/start.sh" ]]; then
  cd "${APP_DIR}"
  exec "${APP_DIR}/build/start.sh"
fi

if [[ -x "${APP_DIR}/build/ros_qt5_gui_app" ]]; then
  cd "${APP_DIR}"
  export LD_LIBRARY_PATH="${APP_DIR}/build/lib:${LD_LIBRARY_PATH:-}"
  exec "${APP_DIR}/build/ros_qt5_gui_app"
fi

if [[ -x "${APP_DIR}/build/install/bin/start.sh" ]]; then
  cd "${APP_DIR}"
  exec "${APP_DIR}/build/install/bin/start.sh"
fi

if [[ -x "${APP_DIR}/install/linux/bin/start.sh" ]]; then
  cd "${APP_DIR}"
  exec "${APP_DIR}/install/linux/bin/start.sh"
fi

if [[ -f "${APP_DIR}/README.md" || -f "${APP_DIR}/README_en.md" ]]; then
  echo "Ros_Qt5_Gui_App source directory found, but no runnable binary was detected." >&2
  echo "Expected one of:" >&2
  echo "  ${APP_DIR}/build/start.sh" >&2
  echo "  ${APP_DIR}/build/ros_qt5_gui_app" >&2
  echo "  ${APP_DIR}/build/install/bin/start.sh" >&2
  echo "  ${APP_DIR}/install/linux/bin/start.sh" >&2
  echo "Please build the external GUI package first, without modifying it from agt_nav_console." >&2
  exit 2
fi

echo "Directory exists but does not look like a Ros_Qt5_Gui_App checkout: ${APP_DIR}" >&2
exit 3
