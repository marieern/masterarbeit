#!/bin/zsh
# --- 01_start_simulation.sh (Korrigiert) ---

# 1. Conda Umgebung laden
eval "$(conda shell.zsh hook)"
conda activate ros_env

# 2. Workspace Setup laden (WICHTIG für Pfade!)
cd ~/ros2_ws
if [ -f "install/setup.zsh" ]; then
    source install/setup.zsh
else
    echo "⚠️ WARNUNG: install/setup.zsh nicht gefunden. Hast du 'colcon build' gemacht?"
fi

# 3. Variablen setzen
export TURTLEBOT3_MODEL=waffle_pi
AWS_PKG_NAME="aws-robomaker-small-warehouse-world"
WORLD_FILE="$HOME/ros2_ws/src/$AWS_PKG_NAME/worlds/my_hybrid_warehouse"

# 4. Modell-Pfade kombinieren (AWS + TurtleBot3 + Standard)
# Wir holen uns dynamisch den Pfad zu den TurtleBot3 Modellen
TB3_MODELS_PATH=$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models
AWS_MODELS_PATH="$HOME/ros2_ws/src/$AWS_PKG_NAME/models"

# Alles zusammenfügen: AWS : TurtleBot : Home-Models : System-Default
export GAZEBO_MODEL_PATH=$AWS_MODELS_PATH:$TB3_MODELS_PATH:$HOME/.gazebo/models:$GAZEBO_MODEL_PATH

echo "🌍 Modell-Pfade gesetzt."
echo "🚀 Starte Gazebo..."

# 5. Starten
ros2 launch gazebo_ros gazebo.launch.py world:="$WORLD_FILE"
