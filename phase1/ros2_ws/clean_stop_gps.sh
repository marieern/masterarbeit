#!/bin/zsh
# Alle hängengebliebenen Lokalisierungs-Knoten killen
pkill -f ekf_node
pkill -f navsat_transform_node
pkill -f gps_gatekeeper

# Den ROS 2 Daemon stoppen und neu starten
ros2 daemon stop
ros2 daemon start
