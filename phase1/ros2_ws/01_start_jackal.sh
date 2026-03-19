#!/bin/zsh
# --- 03_start_jackal_complete.sh ---

eval "$(conda shell.zsh hook)"
conda activate ros_env_jackal
cd ~/ros2_ws
source install/setup.zsh

# Absolute Pfade setzen
AWS_PKG_NAME="aws-robomaker-small-warehouse-world"
WORLD_FILE="$HOME/ros2_ws/src/$AWS_PKG_NAME/worlds/my_hybrid_warehouse"
JACKAL_DESC_PATH="$HOME/ros2_ws/install/jackal_description/share/jackal_description"

export GAZEBO_MODEL_PATH=$HOME/ros2_ws/src/$AWS_PKG_NAME/models:$HOME/ros2_ws/install/$AWS_PKG_NAME/share/$AWS_PKG_NAME/models:$GAZEBO_MODEL_PATH
# Pfad für die Gazebo-Plugins
export GAZEBO_PLUGIN_PATH=$HOME/ros2_ws/install/jackal_description/lib:$GAZEBO_PLUGIN_PATH

# Temporäre Dateipfade
JACKAL_URDF_PATH=/tmp/jackal.urdf
LAUNCH_RSP_PATH=/tmp/start_rsp.launch.py

# 1. URDF aus Xacro erstellen
ros2 run xacro xacro "$HOME/ros2_ws/src/jackal/jackal_description/urdf/jackal.urdf.xacro" -o "$JACKAL_URDF_PATH"

# 2. Verbesserte Launch-Datei erstellen
cat <<EOF > $LAUNCH_RSP_PATH
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    with open('$JACKAL_URDF_PATH', 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        # State Publisher mit Sim Time
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'use_sim_time': True, 'robot_description': robot_desc}]
        ),
        # WICHTIG: Joint State Publisher für die Gelenk-Zeitstempel
        #Node(
         #   package='joint_state_publisher',
          #  executable='joint_state_publisher',
           # parameters=[{'use_sim_time': True}]
        #)
    ])
EOF

# 3. Starten
ros2 launch gazebo_ros gazebo.launch.py world:="$WORLD_FILE" gui:=false &
sleep 5
ros2 launch $LAUNCH_RSP_PATH &
sleep 5
ros2 run gazebo_ros spawn_entity.py -entity jackal -file $JACKAL_URDF_PATH -x 0 -y 0 -z 0.2