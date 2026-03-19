#!/bin/bash
# 02_start_ekf_gps.sh (Ubuntu Version)

# Netzwerkkonfiguration (Identisch zum Mac lassen)
export ROS_DOMAIN_ID=42 
export ROS_LOCALHOST_ONLY=1
#export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp # <--- DIESE ZEILE HINZUFÜGEN

echo "Lade ROS-Umgebung..."
# 1. Unter Ubuntu laden wir ROS global, nicht über Conda/Miniforge
source /opt/ros/humble/setup.bash
# 2. Deinen Workspace laden
source ~/ros2_ws/install/setup.bash

# Hintergrundprozesse säubern
pkill -f ekf_node
pkill -f navsat_transform_node
pkill -f gps_gatekeeper
ros2 daemon stop
ros2 daemon start

echo "Starte Lokalisierung..."
# Der Befehl bleibt gleich, aber wir stellen sicher, dass er im Hintergrund läuft
ros2 launch jackal_control dual_ekf_gps.launch.py use_sim_time:=true &
LAUNCH_PID=$!
sleep 10

echo "Starte RViz..."
# RViz startet unter Linux oft schneller, braucht aber manchmal eine Config-Datei.
# Wenn du eine gespeicherte Config hast, füge "-d pfad/zu/config.rviz" hinzu.
MESA_GL_VERSION_OVERRIDE=3.3 ros2 run rviz2 rviz2 --ros-args -p use_sim_time:=True --log-level warn &
RVIZ_PID=$!

echo "Starte Navigation (Nav2)..."
# WICHTIG: Pfade angepasst auf /home/marieernst
ros2 launch nav2_bringup bringup_launch.py \
    use_sim_time:=True \
    use_composition:=False \
    map:=/home/marieernst/ros2_ws/lager_karte_jackal.yaml \
    params_file:=/home/marieernst/ros2_ws/src/jackal/jackal_navigation/config/nav2_params.yaml

# Cleanup beim Beenden (Strg+C)
trap "kill $LAUNCH_PID $RVIZ_PID; exit" INT
wait
