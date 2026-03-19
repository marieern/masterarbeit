#!/bin/bash

# Orchestrierungs-Skript zum vollautomatischen Starten der hybriden Zustandsschätzung 
# (Dual-EKF + Gatekeeper) sowie des Nav2-Navigations-Stacks.

# === 1. ROS2 NETZWERK-ISOLATION ===
# Setzt die Domain ID und beschränkt die Kommunikation auf Localhost.
# Verhindert Cross-Talk mit anderen ROS2-Netzwerken und garantiert eine 
# isolierte, deterministische Testumgebung für die Evaluation (n=10).
export ROS_DOMAIN_ID=42 
export ROS_LOCALHOST_ONLY=1
# export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp 

echo "Lade ROS-Umgebung..."
# === 2. WORKSPACE INITIALISIERUNG ===
# Laedt die globalen ROS2 Humble Binaries und anschließend den lokalen Workspace.
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# === 3. PROZESS-BEREINIGUNG (CLEANUP) ===
# Beendet gezielt alte Instanzen der Lokalisierungs- und Gatekeeper-Knoten.
# Da EKF-Knoten historische Zustände (Covariance Matrices) im Speicher halten, 
# verhindert dieser Schritt unberechenbare TF-Sprünge (Zombie-Knoten) beim Neustart.
pkill -f ekf_node
pkill -f navsat_transform_node
pkill -f gps_gatekeeper
ros2 daemon stop
ros2 daemon start

echo "Starte hybride Lokalisierung..."
# === 4. DUALE ZUSTANDSSCHÄTZUNG & GATEKEEPER ===
# Startet die in der Arbeit entwickelte Kernarchitektur im Hintergrund.
# 'use_sim_time:=true' synchronisiert die Filter-Zeitstempel zwingend mit der Gazebo-Uhr.
ros2 launch jackal_control dual_ekf_gps.launch.py use_sim_time:=true &
LAUNCH_PID=$!
sleep 10

echo "Starte RViz..."
# === 5. VISUALISIERUNG (RVIZ2) ===
# MESA_GL_VERSION_OVERRIDE=3.3 erzwingt Software-Rendering bzw. Kompatibilität.
# Dieser Workaround ist erforderlich, da in der Testumgebung (wie in Kap. 5 beschrieben) 
# keine dedizierten Linux-GPU-Treiber zur Hardwarebeschleunigung zur Verfügung stehen.
MESA_GL_VERSION_OVERRIDE=3.3 ros2 run rviz2 rviz2 --ros-args -p use_sim_time:=True --log-level warn &
RVIZ_PID=$!

echo "Starte Navigation (Nav2)..."
# === 6. AUTONOME NAVIGATION (NAV2 STACK) ===
# Startet den konfigurierten MPPI-Controller, den Theta*-Planer und die Costmaps.
# 'use_composition:=False' verhindert Threading-Konflikte in ressourcenbeschränkten Umgebungen.
ros2 launch nav2_bringup bringup_launch.py \
    use_sim_time:=True \
    use_composition:=False \
    map:=/home/marieernst/ros2_ws/lager_karte_jackal.yaml \
    params_file:=/home/marieernst/ros2_ws/src/jackal/jackal_navigation/config/nav2_params.yaml

# === 7. GRACEFUL SHUTDOWN ===
# Fängt das Abbruchsignal (Strg+C / SIGINT) ab und beendet alle im Hintergrund 
# gestarteten Prozesse (Lokalisierung und RViz) sauber, um Speicherlecks zu vermeiden.
trap "kill $LAUNCH_PID $RVIZ_PID; exit" INT
wait
