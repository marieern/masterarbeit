#!/bin/bash
# 1. Reste aufräumen
killall -9 gzserver gzclient 2>/dev/null

# 2. Pfade setzen
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:~/ros2_ws/src/aws_robomaker_small_warehouse_world/models:~/.gazebo/models
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# 3. Grafik-Fix für Mac
export LIBGL_ALWAYS_SOFTWARE=1

# 4. Start
echo "Starte Gazebo mit Software-Rendering..."
ros2 launch gazebo_ros gazebo.launch.py world:=/home/marieernst/ros2_ws/src/aws_robomaker_small_warehouse_world/worlds/my_hybrid_warehouse
