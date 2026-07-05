#!/usr/bin/env bash
# Bootstrap ROS 2 workspace for Fanuc M20 + Tesollo DG-3FB MoveIt cell.
set -euo pipefail

WS="${1:-$HOME/ws_fanuc_tesollo}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Workspace: $WS"
mkdir -p "$WS/src"
cd "$WS/src"

clone_if_missing() {
  local dir="$1"
  local url="$2"
  local branch="${3:-}"
  if [[ ! -d "$dir" ]]; then
    if [[ -n "$branch" ]]; then
      git clone --branch "$branch" --depth 1 "$url" "$dir"
    else
      git clone --depth 1 "$url" "$dir"
    fi
  fi
}

# Fanuc arm description + driver (Humble)
clone_if_missing fanuc_description https://github.com/FANUC-CORPORATION/fanuc_description.git
clone_if_missing fanuc_driver https://github.com/FANUC-CORPORATION/fanuc_driver.git humble

# Tesollo gripper meshes + URDF
clone_if_missing delto_b_ros2 https://github.com/tesollodelto/delto_b_ros2.git devel

# This repo's cell packages (symlink)
for pkg in fanuc_tesollo_description df3fb_moveit_config; do
  src="$REPO_ROOT/external/gripper_ros_driver/$pkg"
  dst="$WS/src/$pkg"
  if [[ ! -e "$dst" ]]; then
    ln -sf "$src" "$dst"
    echo "Linked $pkg"
  fi
done

cd "$WS"
source /opt/ros/humble/setup.bash
rosdep update
rosdep install --ignore-src --from-paths src -y || true

colcon build --symlink-install --packages-up-to df3fb_moveit_config
echo ""
echo "Done. Run:"
echo "  source $WS/install/setup.bash"
echo "  ros2 launch df3fb_moveit_config demo.launch.py"
