#!/usr/bin/env python3
"""
localization.launch.py

Step 5 - this brings up map_server + amcl together so the robot can
figure out where it is on the map.

I made this file self-contained (it starts its own map_server) so I can
run it on its own to test, without needing map_loader.launch.py running
first - help.md says to test things independently so tried to keep that
in mind. Both map_server and amcl are lifecycle nodes so one lifecycle
manager handles bringing them both up in order (configure then activate).

how to run:
    ros2 launch testbed_navigation localization.launch.py
    ros2 launch testbed_navigation localization.launch.py \
        map:=/absolute/path/to/other_map.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml

PACKAGE_NAME = 'testbed_navigation'

DEFAULT_MAP = os.path.join(
    get_package_share_directory('testbed_bringup'), 'maps', 'testbed_world.yaml'
)
DEFAULT_AMCL_PARAMS = os.path.join(
    get_package_share_directory(PACKAGE_NAME), 'config', 'amcl_params.yaml'
)


def generate_launch_description():

    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    initial_pose_x = LaunchConfiguration('initial_pose_x')
    initial_pose_y = LaunchConfiguration('initial_pose_y')
    initial_pose_yaw = LaunchConfiguration('initial_pose_yaw')

    declare_map_cmd = DeclareLaunchArgument(
        'map',
        default_value=DEFAULT_MAP,
        description='Full path to the map yaml file to load')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=DEFAULT_AMCL_PARAMS,
        description='Full path to the AMCL parameters file')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically bring map_server/amcl up to the active state')

    # these defaults match where the robot actually spawns in gazebo
    # (see spawn_testbed.launch.py - position=[0.0, 5.0, 0.0], orientation=[0.0, 0.0, 0.0])
    # so amcl starts off already knowing roughly where the robot is
    declare_initial_pose_x_cmd = DeclareLaunchArgument(
        'initial_pose_x', default_value='0.0',
        description='Initial pose X to seed AMCL with, in the map frame')
    declare_initial_pose_y_cmd = DeclareLaunchArgument(
        'initial_pose_y', default_value='5.0',
        description='Initial pose Y to seed AMCL with, in the map frame')
    declare_initial_pose_yaw_cmd = DeclareLaunchArgument(
        'initial_pose_yaw', default_value='0.0',
        description='Initial pose yaw (radians) to seed AMCL with, in the map frame')

    # this rewrites use_sim_time inside the yaml file to match whatever was
    # passed in on the command line, otherwise the yaml value and the launch
    # arg could end up disagreeing with each other
    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True)

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': map_yaml_file,
            'use_sim_time': use_sim_time,
        }]
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[configured_params]
    )

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': ['map_server', 'amcl'],
        }]
    )

    # so this part took me a while to figure out - amcl has a
    # set_initial_pose option in amcl_params.yaml that's supposed to auto
    # seed the initial pose, but it just wasn't working reliably for me on
    # this Humble setup. AMCL would just sit there printing "AMCL cannot
    # publish a pose or update the transform. Please set the initial
    # pose..." forever and never actually publish map -> odom.
    # workaround: wait a few seconds (give map_server/amcl time to actually
    # configure and activate first) then manually publish one /initialpose
    # message myself with ros2 topic pub. Works every time. You can still
    # just click "2D Pose Estimate" in rviz afterward if you want to
    # correct/refine it.
    seed_initial_pose = TimerAction(
        period=6.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ros2', 'topic', 'pub', '-1', '/initialpose',
                    'geometry_msgs/msg/PoseWithCovarianceStamped',
                    [
                        '{header: {frame_id: "map"}, pose: {pose: {',
                        'position: {x: ', initial_pose_x, ', y: ', initial_pose_y, ', z: 0.0}, ',
                        'orientation: {z: 0.0, w: 1.0}}, ',
                        'covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, ',
                        '0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.06853891945200942]}}',
                    ],
                ],
                output='screen',
            )
        ],
    )

    ld = LaunchDescription()
    ld.add_action(declare_map_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_initial_pose_x_cmd)
    ld.add_action(declare_initial_pose_y_cmd)
    ld.add_action(declare_initial_pose_yaw_cmd)
    ld.add_action(map_server_node)
    ld.add_action(amcl_node)
    ld.add_action(lifecycle_manager_node)
    ld.add_action(seed_initial_pose)
    return ld
