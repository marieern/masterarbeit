# Masterarbeit: Hybride Navigation für das Jackal UGV
Evaluierung und prototypische Umsetzung autonomer Navigationslösungen für innerbetriebliche Transportfahrzeuge (Jackal UGV) mit Open-Source-Software in einer hybriden (Indoor/Outdoor) Logistikumgebung.

## Projekt- und Metadaten
* **Autorin:** Marie Ernst
* **Zeitraum der Softwareentwicklung:** Dezember 2025 bis März 2026
* **Datenformate & Größe:** Das Repository umfasst insgesamt ca. 1.3 GB. Vorliegende Dateiformate sind primär Python-Skripte (`.py`), Shell-Skripte (`.sh`), ROS2-Launch-Files (`.py`), Konfigurationsdateien (`.yaml`), Roboterbeschreibungen (`.urdf.xacro`) sowie C++-Skripte.
* **Qualitätssicherung:** Die Funktionalität des Codes wurde durch systematische Versuchsreihen in der Gazebo-Simulation validiert.
* **Datenschutz:** Im Rahmen dieses Softwareprojekts wurden ausschließlich maschinelle Sensordaten simuliert. Es wurden keine personenbezogenen Daten erhoben oder verarbeitet.

## Verwendete Werkzeuge
* **OS:** Ubuntu 22.04 LTS (https://releases.ubuntu.com/22.04/)
* **Middleware:** ROS 2 Humble Hawksbill (https://docs.ros.org/en/humble/)
* **Simulation:** Gazebo (via `gazebo_ros_pkgs` für ROS 2 Humble)
* **Sprachen:** Python 3.10, XML, YAML, Bash
* **Hardware-Anforderung:** Standard-PC, keine dedizierte GPU erforderlich.

---

## Kern-Features
Im Rahmen dieser Masterarbeit wurden Standard-ROS2-Komponenten gezielt für die Herausforderungen der Intralogistik modifiziert und erweitert:
1. **Dual-EKF-Architektur:** Nahtlose Transition zwischen GNSS-basierter (Outdoor) und AMCL-basierter (Indoor) Zustandsschätzung.
2. **Gatekeeper-Modul:** Eigens entwickelte Logik (`gps_gatekeeper.py`) zur Filterung von Multipath-Effekten an Hallenfassaden und zur Durchführung dynamischer Koordinaten-Resets (Hard-Reset) am Hallentor.
3. **Skid-Steer-Optimierung:** Anpassung der Nav2-MPPI-Kritiker und lokale IMU-Fusion zur Vermeidung von Trajektorien-Fehlern durch mechanischen Radschlupf.
4. **Gabelzinken-Erkennung:** Integration und Evaluierung eines abwärts geneigten LiDAR-Sensors zur sicheren Detektion bodennaher Störkanten (Flurförderzeuge).

## Installationsguide
Zum automatisierten Aufsetzen der Umgebung kann das Skript `robot_setup.sh` ausgeführt werden. Dieses installiert alle benötigten Abhängigkeiten:
1. Python3 & Build-Tools
2. ROS 2 Humble Repository
3. Fehlende Sensor-Bibliotheken (z. B. `ros-humble-gazebo-plugins`, `ros-humble-xacro`)
4. Klonen der `aws-warehouse-world` in den Workspace
5. Setzen der Umgebungskonfigurationen
6. Installation von RViz2

## Ordnerübersicht - Wichtige Dateien
Die Dateien, die im Rahmen dieser Arbeit hauptsächlich erarbeitet und angepasst wurden, sind:

**Start-Skripte:**
* `ros2_ws/jackal_gui.sh`
* `ros2_ws/start_ekf_gps.sh`
* `ros2_ws/02_start_mapping_logic.sh`
* `ros2_ws/03_save_map.sh`
* `ros2_ws/04_navigation.sh`

**Umgebung & Konfiguration:**
* `ros2_ws/src/aws-robomaker-small-warehouse-world/worlds/my_hybrid_warehouse`
* `ros2_ws/src/jackal/jackal_control/config/ekf.yaml`
* `ros2_ws/src/jackal/jackal_navigation/config/nav2_params.yaml`
* `ros2_ws/src/jackal/jackal_navigation/behavior_trees/jackal_nav_recovery.xml`

**Logik & Architektur:**
* `ros2_ws/src/jackal/jackal_control/launch/dual_ekf_gps.launch.py`
* `ros2_ws/src/jackal/jackal_control/src/gps_gatekeeper.py`
* `ros2_ws/src/jackal/jackal_description/urdf/jackal.urdf.xacro`
* `ros2_ws/src/jackal/jackal_description/urdf/jackal_sensors.urdf.xacro`
* `ros2_ws/src/jackal/jackal_navigation/launch/master_bringup.launch.py`

**Struktur-Hinweis:** 
* Der Ordner `phase1/ros2_ws` enthält aus Transparenzgründen alle im Laufe der Arbeit entstandenen Dateien, auch solche, die nicht für das finale Ergebnis verwendet wurden.
* Der Ordner `phase2/ros2_ws` enthält nur Dateien, die für das Ergebnis der Arbeit wirklich genutzt wurden. Zudem enthalten Dateien in diesem Ordner die finalen Kommentare. Beide Ordner enthalten Dateien, die mithilfe von Gemini überarbeitet und kommentiert wurden.
* *Anmerkung zu Pfaden:* Beim Bearbeiten lag der `ros2_ws` Ordner direkt im Home-Verzeichnis. Sollte es zu Pfadproblemen kommen, verschieben Sie den `ros2_ws` Ordner aus `phase1` bzw. `phase2` direkt in Ihr Home-Verzeichnis. Die Trennung in diese Ordner dient lediglich der Übersichtlichkeit im GitHub-Repository.

## Anwendung starten

**1. AWS-Pfade anpassen:**
Bevor die Anwendung gestartet werden kann, müssen die Pfade in der World-Datei an den lokalen PC angepasst werden. Führe dazu folgenden Befehl aus (ersetze `marieernst` ggf. durch deinen Benutzernamen):
```
sed -i "s|model://aws_robomaker_small_warehouse_world|${HOME}/ros2_ws/src/aws-robomaker-small-warehouse-world/models|g" ~/ros2_ws/src/aws-robomaker-small-warehouse-world/worlds/my_hybrid_warehouse
```

**2. Workspace bauen:**
Öffne ein Terminal im ros2_ws Ordner und baue den Code:
```
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

**3. Simulation starten:**
Starte zuerst die Gazebo-Simulation und die TF-Publisher:

```
./jackal_gui.sh
```

**4. Navigations-Stack starten:**
Öffne ein neues Terminal, navigiere in den ros2_ws Ordner, source die Umgebung erneut und starte den EKF und Nav2.
ACHTUNG: Das jackal_gui.sh Skript muss vollständig hochgefahren sein, bevor dieser Schritt ausgeführt wird!

```
source install/setup.bash
./start_ekf_gps.sh
```

**5. Roboter navigieren:**
Sobald RViz gestartet ist, kann dem Jackal UGV über das Tool "2D Goal Pose" (in der oberen Menüleiste von RViz) ein Navigationsziel auf der Karte zugewiesen werden.

## Mögliche Fehlerbehandlung (Troubleshooting)

**1. Multicast-Fehler bei der Discovery:**
Sollte bei der Ausführung des jackal_gui.sh Skripts die Meldung "selected interface 'lo' is not multicast-capable: disabling multicast" erscheinen, wird die Kommunikation der Knoten blockiert. Führe folgenden Befehl aus und starte das Skript neu:
Bash
```
sudo ip link set lo multicast on
```
**2. Zombie-Prozesse nach Abbruch:**
Wenn das jackal_gui.sh oder start_ekf_gps.sh Skript einmal gestartet und mit Strg+C beendet wurde, sollten vor einem Neustart alle verwaisten Hintergrundprozesse bereinigt werden:
Bash
```
killall -9 rviz2 gazebo gzserver gzclient _ros2_daemon joint_state_publisher nav_metrics_logger robot_state_publisher
```
**3. Warnung beim Map-Status:**
Sollte der Status der Map in RViz auf Warning stehen, beende das start_ekf_gps.sh Skript mittels Strg+C und führe es erneut aus, um die TF-Synchronisation der Filter neu anzustoßen.
