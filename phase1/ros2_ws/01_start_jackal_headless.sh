#!/bin/zsh
# --- 02_start_jackal_headless.sh ---

eval "$(conda shell.zsh hook)"
conda activate ros_env_jackal
cd ~/ros2_ws
source install/setup.zsh

# Pfade setzen
AWS_PKG_NAME="aws-robomaker-small-warehouse-world"
WORLD_FILE="$HOME/ros2_ws/src/$AWS_PKG_NAME/worlds/my_hybrid_warehouse"
JACKAL_URDF_PATH=/tmp/jackal.urdf
LAUNCH_RSP_PATH=/tmp/start_rsp.launch.py
RVIZ_CONFIG="$HOME/ros2_ws/jackal_low_cpu.rviz"

# 1. URDF aus Xacro erstellen
ros2 run xacro xacro "$HOME/ros2_ws/src/jackal/jackal_description/urdf/jackal.urdf.xacro" -o "$JACKAL_URDF_PATH"

# 2. Temporäre Launch-Datei für den Robot State Publisher erstellen
cat <<EOF > $LAUNCH_RSP_PATH
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    with open('$JACKAL_URDF_PATH', 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'use_sim_time': True, 
                'robot_description': robot_desc
            }]
        )
    ])
EOF

# 3. Gazebo im HEADLESS Modus starten (spart CPU)
ros2 launch gazebo_ros gazebo.launch.py world:="$WORLD_FILE" gui:=false &
sleep 6

# 4. Robot State Publisher über die Launch-Datei starten (behebt den Absturz)
ros2 launch $LAUNCH_RSP_PATH &
sleep 3

# 5. Jackal in Gazebo spawnen
ros2 run gazebo_ros spawn_entity.py -entity jackal -file $JACKAL_URDF_PATH -x 0 -y 0 -z 0.2 &
sleep 3

# 6. Rviz2 mit der sparsamen Konfiguration starten
rviz2 -d $RVIZ_CONFIG --ros-args -p use_sim_time:=true &

echo "Simulation erfolgreich gestartet!"