#!/bin/bash

# Skript zum initialen Hochfahren der Gazebo-Simulation und der statischen TF-Transformationen.
# Optimiert fuer den Headless-Betrieb (ohne GUI), um CPU-Ressourcen zu schonen.

cd ~/ros2_ws
source install/setup.bash

# === 1. PFAD-KONFIGURATION ===
AWS_PKG_NAME="aws-robomaker-small-warehouse-world"
WORLD_FILE="$HOME/ros2_ws/src/$AWS_PKG_NAME/worlds/my_hybrid_warehouse"
JACKAL_DESC_PATH="$HOME/ros2_ws/install/jackal_description/share/jackal_description"

# === 2. ROS2 NETZWERK-ISOLATION ===
# Verhindert Cross-Talk mit anderen ROS2-Systemen im selben WLAN/Netzwerk.
# wichtig fuer deterministische Tests und den ungestoerten Betrieb des MPPI-Controllers.
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=42 # Eigener Sub-Namespace für diese Simulation

# === 3. GAZEBO UMGEBUNGSVARIABLEN ===
# Macht die 3D-Modelle der Halle (Paletten, Regale) und die Skid-Steer/Laser-Plugins fuer Gazebo auffindbar
export GAZEBO_MODEL_PATH=$HOME/ros2_ws/src/$AWS_PKG_NAME/models:$HOME/ros2_ws/install/$AWS_PKG_NAME/share/$AWS_PKG_NAME/models:$GAZEBO_MODEL_PATH
export GAZEBO_PLUGIN_PATH=$HOME/ros2_ws/install/jackal_description/lib:$GAZEBO_PLUGIN_PATH

# Temporaere Dateipfade fuer die On-the-Fly-Generierung
JACKAL_URDF_PATH=/tmp/jackal.urdf
LAUNCH_RSP_PATH=/tmp/start_rsp.launch.py

# === 4. DYNAMISCHE URDF-GENERIERUNG ===
# Kompiliert das XACRO-Modell in ein statisches URDF-Format fuer Gazebo
ros2 run xacro xacro "$HOME/ros2_ws/src/jackal/jackal_description/urdf/jackal.urdf.xacro" is_sim:=true -o "$JACKAL_URDF_PATH"

# === 5. ON-THE-FLY LAUNCH-FILE ===
# Generiert dynamisch eine Python-Launch-Datei fuer die TF-Publisher. Dieser Ansatz garantiert, dass das generierte URDF fehlerfrei eingelesen wird
cat <<EOF > $LAUNCH_RSP_PATH
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    with open('$JACKAL_URDF_PATH', 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        # Robot State Publisher: Publiziert den statischen TF-Baum (z.B. base_link -> laser).
        # 'use_sim_time' ist kritisch, da sonst die Laser-Scans in RViz zeitlich zittern
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'use_sim_time': True, 'robot_description': robot_desc}]
        ),
        # Joint State Publisher: Generiert kontinuierlich aktuelle Zeitstempel fuer die Rad-Gelenke. Verhindert TF-Fehler bei der Rad-Odometrie des Skid-Steer-Antriebs.
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            parameters=[{'use_sim_time': True}]
        )
    ])
EOF

# === 6. SYSTEM-START ===

# Startet die Gazebo-Welt im Headless-Modus (gui:=false). 
# Das spart GPU/CPU-Leistung und haelt den Real-Time Factor (RTF) der Simulation stabil.
ros2 launch gazebo_ros gazebo.launch.py world:="$WORLD_FILE" gui:=false use_sim_time:=true &
# Wartet 5 Sekunden, damit die Physik-Engine vollstaendig in den Speicher geladen ist
sleep 5 

# Startet den generierten State Publisher zur Bereitstellung des TF-Baums
ros2 launch $LAUNCH_RSP_PATH use_sim_time:=true &
sleep 5

# Spawnt das physische Jackal-Modell an den definierten Startkoordinaten (x=0, y=0) in die Halle.
ros2 run gazebo_ros spawn_entity.py -entity jackal -file $JACKAL_URDF_PATH -x 0.00 -y 0.00 -z 0.2
