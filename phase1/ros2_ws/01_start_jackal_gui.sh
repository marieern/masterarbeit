#!/bin/zsh
# --- Stabilisiertes Start-Skript ---

# 1. Radikaler Cleanup (Verhindert 'Already Registered' Warnung)
pkill -9 -f "robot_state_publisher|ekf_node|navsat_transform|gzserver|gzclient"
ros2 daemon stop && ros2 daemon start

eval "$(conda shell.zsh hook)"
conda activate ros_env_jackal
cd ~/ros2_ws
source install/setup.zsh

# Pfade setzen
AWS_PKG_NAME="aws-robomaker-small-warehouse-world"
WORLD_FILE="$HOME/ros2_ws/src/$AWS_PKG_NAME/worlds/my_hybrid_warehouse"
JACKAL_URDF_PATH=/tmp/jackal.urdf
LAUNCH_RSP_PATH=/tmp/start_rsp.launch.py

# 2. URDF erstellen (Deine bewährte Methode)
ros2 run xacro xacro "$HOME/ros2_ws/src/jackal/jackal_description/urdf/jackal.urdf.xacro" is_sim:=true -o "$JACKAL_URDF_PATH"

# 3. Launch-Datei erstellen (Deine bewährte Methode)
cat <<EOF > $LAUNCH_RSP_PATH
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    with open('$JACKAL_URDF_PATH', 'r') as infp:
        robot_desc = infp.read()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'use_sim_time': True, 'robot_description': robot_desc}])
    ])
EOF

# Start-Reihenfolge mit mehr Puffer für den Mac
echo "Starte Gazebo..."
ros2 launch gazebo_ros gazebo.launch.py world:="$WORLD_FILE" gui:=false &

# Warten bis der /spawn_entity Service wirklich da ist (Beweis, dass Gazebo bereit ist)
echo "Warte auf Gazebo-Bereitschaft..."
until ros2 service list | grep -q '/spawn_entity'; do
  sleep 2
done

# 4. robot_state_publisher NICHT im Hintergrund, sondern kontrolliert
echo "Starte robot_state_publisher..."
# Wir nutzen 'timeout', um den Befehl nach dem Start 'laufen' zu lassen, ohne das Skript zu blockieren
ros2 launch $LAUNCH_RSP_PATH & 

# WICHTIG: Prüfen, ob der Knoten wirklich erschienen ist
sleep 5
if ! ros2 node list | grep -q "/robot_state_publisher"; then
    echo "RSP nicht gefunden, versuche alternativen Start..."
    ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=true -p robot_description:="$(cat $JACKAL_URDF_PATH)" &
fi

# 5. Erst ganz am Ende spawnen
sleep 5
ros2 run gazebo_ros spawn_entity.py -entity jackal -file $JACKAL_URDF_PATH -x 0 -y 0 -z 0.2