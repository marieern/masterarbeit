# 1. Beende alle ROS-Hintergrunddienste
ros2 daemon stop

# 2. Beende alle Gazebo- und ROS-Prozesse
pkill -9 gzserver; pkill -9 gzclient; pkill -9 robot_state_publisher

# 3. Setze die Variablen neu (OHNE die XML-Datei)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=42

# 4. Starte den Dienst sauber neu
ros2 daemon start
