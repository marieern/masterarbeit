import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command, LaunchConfiguration

def generate_launch_description():
    # Pfade zu den benoetigten ROS2-Paketen
    pkg_control = get_package_share_directory('jackal_control')
    pkg_nav = get_package_share_directory('jackal_navigation')
    pkg_description = get_package_share_directory('jackal_description')
    pkg_aws_world = get_package_share_directory('aws_robomaker_small_warehouse_world')

    # Globale Simulationszeit aktivieren (erforderlich fuer synchrone Gazebo-TF-Daten)
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Simulationsumgebung (Gazebo)
    # Startet Gazebo im Headless-Modus (gui: false), um CPU-Ressourcen fuer den MPPI-Controller und die Costmaps freizugeben
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': os.path.join(pkg_aws_world, 'worlds', 'my_hybrid_warehouse'),
            'gui': 'false',
            'use_sim_time': use_sim_time 
        }.items()
    )

    # Robot State Publisher 
    # Parst die XACRO-Datei in URDF und publiziert den statischen TF-Baum des Roboters
    robot_description_content = Command(['xacro ', os.path.join(pkg_description, 'urdf', 'jackal.urdf.xacro'), ' is_sim:=true'])
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_content, 'use_sim_time': use_sim_time}]
    )

    # Roboter in Gazebo spawnen 
    # Eine TimerAction (5s) verzoegert den Spawn, um sicherzustellen, dass die Gazebo-Welt vollstaendig im Speicher geladen ist, bevor die Physik-Engine greift
    spawn_jackal = TimerAction(
        period=5.0,
        actions=[Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=['-topic', 'robot_description', '-entity', 'jackal', '-x', '0', '-y', '0', '-z', '1'],
            parameters=[{'use_sim_time': use_sim_time}] 
        )]
    )
    
    # Eigene hybride Lokalisierung
    # Startet die in der Arbeit entwickelte Dual-EKF-Architektur inkl. Gatekeeper-Logik
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_control, 'launch', 'dual_ekf_gps.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Nav2
    # bindet den modifizierten Nav2-Stack mit den spezifischen Costmap-Layern und den MPPI/Theta*-Parametern ein.
    map_path = os.path.join(pkg_nav, 'maps', 'lager_karte_jackal.yaml')
    nav_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': os.path.join(pkg_nav, 'config', 'nav2_params.yaml'),
            'map': map_path,
            'autostart': 'true'
        }.items()
    )

    # Visualisierung in Rviz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        gazebo_launch,
        robot_state_publisher,
        spawn_jackal,
        localization_launch,
        nav_bringup_launch,
        rviz_node
    ])
