import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_share = get_package_share_directory('jackal_control')
    ekf_config_path = os.path.join(pkg_share, 'config', 'ekf.yaml')
    # use_sim_time wird benoetigt damit die EKF-Knoten synchron zur Gazebo-Uhrzeit laufen und TF-Transformationen nicht verfallen.
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        # 1. Lokaler EKF (odom -> base_link)
        # Berechnet die kontinuierliche, hochfrequente lokale Odometrie durch Fusion von Rad-Encodern und IMU. Dieser Filter ist von globalen Korrektursprüngen 
        # (GNSS/AMCL) entkoppelt, um den MPPI-Controller nicht zu destabilisieren
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            parameters=[ekf_config_path, {'use_sim_time': use_sim_time}],
            remappings=[('/odometry/filtered', '/odometry/local')]
        ),

        # 2. Globaler EKF (map -> odom)
        # Erweitert die lokale Odometrie um absolute Positionsreferenzen (GNSS/AMCL).
        # Berechnet die Transformation zwischen Welt-Koordinaten (map) und der lokalen Startposition (odom)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            parameters=[ekf_config_path, {'use_sim_time': use_sim_time}],
            remappings=[('/odometry/filtered', '/odometry/global')]
        ),

        # 3. Navsat Transform
        # Konvertiert die geodätischen GPS-Koordinaten (Längen-/Breitengrad) in das kartesische map-Koordinatensystem des Roboters
        Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform',
            output='screen',
            parameters=[ekf_config_path, {'use_sim_time': use_sim_time}],
            remappings=[
                ('/imu/data', '/imu'),
                ('/gps/fix', '/gps/fix'),
                ('/odometry/filtered', '/odometry/local'),
                # leitet das GPS in "Raw"-Kanal um
                ('/odometry/gps', '/odometry/gps_raw') 
            ]
        ),

        # 4. Gatekeeper
        # Eigene Implementierung zur Orchestrierung der Indoor/Outdoor-Transitionen
        # Filtert Multipath-Fehler an der Hallenfassade, gibt validierte GNSS-Daten an den globalen EKF weiter und triggert Costmap-Bereinigungen sowie Hard-Resets
        Node(
            package='jackal_control',
            executable='gps_gatekeeper.py',
            name='gps_gatekeeper',
            parameters=[{'use_sim_time': use_sim_time}]
        )
    ])
