#!/bin/zsh
# --- 04_navigation.sh ---

if [ -z "$CONDA_PREFIX" ]; then
    eval "$(conda shell.zsh hook)"
    conda activate ros_env
fi
cd ~/ros2_ws
source install/setup.zsh
export TURTLEBOT3_MODEL=waffle_pi

# Pfad zur gespeicherten Karte (bitte Namen anpassen falls anders!)
MAP_FILE="/home/marieernst/ros2_ws/lager_karte_3.yaml"

echo "🗺️ Lade Navigation mit Karte: $MAP_FILE"

# Wir suchen wieder die URDF Datei für den Körper (wie beim Mapping)
URDF_FILE=$(find $CONDA_PREFIX -name "turtlebot3_waffle_pi.urdf*" | head -n 1)

# 1. Robot State Publisher starten (Hintergrund)
if [[ "$URDF_FILE" == *".xacro"* ]]; then
    ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=True -p robot_description:="$(xacro $URDF_FILE)" &
else
    ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=True -p robot_description:="$(cat $URDF_FILE)" &
fi

# 2. Navigation starten
# Startet AMCL (Lokalisierung) und Navigation (Pfadplanung)
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True map:="$MAP_FILE"
