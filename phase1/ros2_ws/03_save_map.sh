#!/bin/zsh
# --- 03_save_map.sh ---
eval "$(conda shell.zsh hook)"
conda activate ros_env

MAP_NAME="lager_karte_jackal"
echo "💾 Speichere Karte als '$MAP_NAME'..."
ros2 run nav2_map_server map_saver_cli -f $MAP_NAME
