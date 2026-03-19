#!/bin/bash
# 01_simulation_safe.sh - Safe Mode für Retina Displays

echo "--- 1. Resetting Gazebo Config ---"
# Wir setzen die Fenstergröße zurück, damit es nicht in 4K startet (zu langsam für CPU)
mkdir -p ~/.gazebo
cat <<EOF > ~/.gazebo/gui.ini
[geometry]
x=0
y=0
width=1024
height=768
EOF

echo "--- 2. Aufräumen ---"
pkill -f gzserver
pkill -f gzclient
pkill -f robot_state_publisher
ros2 daemon stop
sleep 1

echo "--- 3. Umgebung laden ---"
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# ### FIXES FÜR MAC LINUX ###
# 1. Software Rendering erzwingen (Verhindert den Absturz "px != 0")
export LIBGL_ALWAYS_SOFTWARE=1
# 2. Wayland Fix
export QT_QPA_PLATFORM=xcb

# ### ROS NETZWERK ###
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp 

# ### PFADE ###
JACKAL_URDF_PATH=/tmp/jackal.urdf
export GAZEBO_PLUGIN_PATH=/opt/ros/humble/lib:$HOME/ros2_ws/install/jackal_description/lib
export GAZEBO_MODEL_PATH=$HOME/ros2_ws/install/jackal_description/share/jackal_description/meshes

echo "--- 4. Generiere URDF ---"
ros2 run xacro xacro $(ros2 pkg prefix jackal_description)/share/jackal_description/urdf/jackal.urdf.xacro is_sim:=true -o "$JACKAL_URDF_PATH"

echo "--- 5. Starte Gazebo (Safe Mode) ---"
# Wir starten PAUSIERT, damit der PC Zeit hat
ros2 launch gazebo_ros gazebo.launch.py gui:=true pause:=true &
GAZEBO_PID=$!

echo "--- WARTE (Geduld...) ---"
sleep 15

echo "--- 6. Spawne Jackal ---"
ros2 run gazebo_ros spawn_entity.py -entity jackal -file $JACKAL_URDF_PATH -x 0 -y 0 -z 0.5

echo "--- 7. Starte Robot State Publisher ---"
ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=true -p robot_description:="$(cat $JACKAL_URDF_PATH)" &

echo "------------------------------------------------"
echo "WICHTIG:"
echo "1. Wenn Ubuntu fragt 'Antwortet nicht' -> Klicke auf 'WARTEN' (Wait)."
echo "2. Drücke im Gazebo Fenster unten links auf PLAY."
echo "------------------------------------------------"
wait $GAZEBO_PID
