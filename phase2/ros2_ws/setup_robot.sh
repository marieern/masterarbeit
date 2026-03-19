#!/bin/bash
# --- FINAL SETUP: Inklusive Gazebo-Sensor-Plugins, RViz und AWS World ---
set -e

echo ">>> 1. Basissystem & Build-Tools..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl gnupg2 lsb-release build-essential \
    python3-pip python3-rosdep python3-dev git \
    python3-colcon-common-extensions dos2unix netpbm imagemagick

echo ">>> 2. ROS 2 Humble Repository..."
if [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
fi
sudo apt update

echo ">>> 3. DIE FEHLENDEN SENSOR- & ROS-BIBLIOTHEKEN..."
# 'ros-humble-desktop' enthält bereits rviz2, wird hier aber zur Sicherheit explizit geladen.
# 'xacro' ist zwingend für die URDF-Generierung des Jackal UGV nötig!
sudo apt install -y \
    ros-humble-desktop \
    ros-humble-rviz2 \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-plugins \
    ros-humble-sensor-msgs \
    ros-humble-robot-localization \
    ros-humble-tf-transformations \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-joint-state-publisher \
    ros-humble-xacro \
    ros-humble-pcl-ros \
    ros-humble-twist-mux \
    ros-humble-topic-tools

echo ">>> 4. AWS Small Warehouse World herunterladen..."
# Die AWS-Welt ist kein apt-Paket und muss in den Workspace geklont werden.
WORKSPACE_SRC="$HOME/ros2_ws/src"
AWS_REPO_DIR="$WORKSPACE_SRC/aws-robomaker-small-warehouse-world"

mkdir -p "$WORKSPACE_SRC"
if [ ! -d "$AWS_REPO_DIR" ]; then
    echo "Klone AWS Warehouse World in den Workspace..."
    git clone https://github.com/aws-robotics/aws-robomaker-small-warehouse-world.git "$AWS_REPO_DIR" -b ros2
else
    echo "AWS Warehouse World existiert bereits im Workspace."
fi

echo ">>> 5. Umgebungskonfiguration..."
BASHRC="$HOME/.bashrc"
grep -q "export QT_QPA_PLATFORM=xcb" "$BASHRC" || echo "export QT_QPA_PLATFORM=xcb" >> "$BASHRC"
grep -q "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" "$BASHRC" || echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> "$BASHRC"
grep -q "source /opt/ros/humble/setup.bash" "$BASHRC" || echo "source /opt/ros/humble/setup.bash" >> "$BASHRC"

echo "========================================================="
echo "Installation komplett! Bitte Terminal neu starten."
echo "Danach im Workspace: colcon build --symlink-install"
echo "========================================================="
