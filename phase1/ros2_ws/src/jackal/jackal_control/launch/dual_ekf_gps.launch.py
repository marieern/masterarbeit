import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_share = get_package_share_directory('jackal_control')
    ekf_config_path = os.path.join(pkg_share, 'config', 'ekf.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        # 1. Lokaler EKF (odom -> base_link)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            parameters=[ekf_config_path, {'use_sim_time': use_sim_time}],
            remappings=[('/odometry/filtered', '/odometry/local')]
        ),

        # 2. Globaler EKF (map -> odom)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            parameters=[ekf_config_path, {'use_sim_time': use_sim_time}],
            remappings=[('/odometry/filtered', '/odometry/global')]
        ),

        # 3. Navsat Transform
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
                # WICHTIG: Diese Zeile hat gefehlt!
                # Sie leitet das GPS in unseren "Raw"-Kanal um.
                ('/odometry/gps', '/odometry/gps_raw') 
            ]
        ),

        # 4. Gatekeeper
        Node(
            package='jackal_control',
            executable='gps_gatekeeper.py',
            name='gps_gatekeeper',
            parameters=[{'use_sim_time': use_sim_time}]
        )
    ])
