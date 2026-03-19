#!/bin/zsh
# --- 02_start_mapping_logic.sh ---

eval "$(conda shell.zsh hook)"
conda activate ros_env
export TURTLEBOT3_MODEL=waffle_pi

echo "🔍 Suche URDF-Datei in Conda Umgebung..."
# Sucht automatisch nach der Datei (egal ob .urdf oder .xacro)
URDF_FILE=$(find $CONDA_PREFIX -name "turtlebot3_waffle_pi.urdf*" | head -n 1)

if [ -z "$URDF_FILE" ]; then
    echo "❌ FEHLER: Keine URDF Datei gefunden! Bitte 'ros-humble-turtlebot3-description' installieren."
    exit 1
fi
echo "✅ Gefunden: $URDF_FILE"

# 1. Robot State Publisher im HINTERGRUND starten (& am Ende)
echo "🤖 Starte Robot State Publisher (Körper)..."
if [[ "$URDF_FILE" == *".xacro"* ]]; then
    # Wenn es eine Xacro Datei ist
    ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=True -p robot_description:="$(xacro $URDF_FILE)" &
else
    # Wenn es eine reine URDF Datei ist (dein Fall)
    ros2 run robot_state_publisher robot_state_publisher --ros-args -p use_sim_time:=True -p robot_description:="$(cat $URDF_FILE)" &
fi
RSP_PID=$! # Merken uns die Prozess-ID

# Kurz warten, damit TF da ist
sleep 3

# 2. SLAM Toolbox starten
echo "🧠 Starte SLAM Toolbox (Mapping)..."
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=True

# Wenn SLAM beendet wird, beende auch den Hintergrund-Prozess
kill $RSP_PID
