#!/usr/bin/env python3
"""
navigation.launch.py

This is step 6 - basically starting up all the individual nav2 nodes
myself instead of just using the nav2_bringup launch files (that's the
point of the assignment i think, to actually see what's underneath).

nodes being started here:
  - controller_server   -> this is the local planner (uses DWB)
  - planner_server       -> global planner (NavFn)
  - behavior_server      -> recovery behaviors, spin/backup/wait etc
  - bt_navigator          -> runs the behavior tree for NavigateToPose
  - waypoint_follower
  - velocity_smoother
  - collision_monitor
All of these get managed together by one lifecycle manager at the bottom,
same idea as what nav2_bringup does under the hood, just written out
explicitly here so it's clearer what's actually running.

This also includes localization.launch.py (map_server + amcl) so running
just this one file gives you localization + navigation together:

    ros2 launch testbed_navigation navigation.launch.py

(map_loader.launch.py, localization.launch.py and this file can still all
be run separately too, that was one of the requirements)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml

PACKAGE_NAME = 'testbed_navigation'

DEFAULT_NAV2_PARAMS = os.path.join(
    get_package_share_directory(PACKAGE_NAME), 'config', 'nav2_params.yaml'
)
DEFAULT_RVIZ_CONFIG = os.path.join(
    get_package_share_directory(PACKAGE_NAME), 'rviz', 'nav2_default_view.rviz'
)

# list of all the lifecycle nodes in this file, the lifecycle manager
# needs this list to know which nodes to configure/activate
LIFECYCLE_NODES = [
    'controller_server',
    'planner_server',
    'behavior_server',
    'bt_navigator',
    'waypoint_follower',
    'velocity_smoother',
    'collision_monitor',
]


def generate_launch_description():

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    use_rviz = LaunchConfiguration('use_rviz')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=DEFAULT_NAV2_PARAMS,
        description='Full path to the nav2 parameters file (planner/controller/bt/etc.)')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically bring the navigation stack up to the active state')

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Whether to start RViz with the navigation view')

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key='',
            param_rewrites={'use_sim_time': use_sim_time},
            convert_types=True),
        allow_substs=True)

    # start localization first (map_server + amcl) - localization.launch.py
    # already has its own lifecycle manager set up for those two so i don't
    # need to redo that here, just include the whole file
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory(PACKAGE_NAME),
                         'launch', 'localization.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'autostart': autostart,
        }.items()
    )

    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[configured_params],
    )

    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[configured_params],
    )

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[configured_params],
    )

    waypoint_follower_node = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[configured_params],
    )

    velocity_smoother_node = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=[configured_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    # note to self on how the velocity commands actually flow through here:
    # controller_server publishes on 'cmd_vel_nav' -> velocity_smoother reads
    # that and publishes 'cmd_vel_smoothed' -> collision_monitor takes that
    # in and publishes the final 'cmd_vel' (topic names set in
    # nav2_params.yaml) -> and that's what the gazebo diff_drive plugin
    # actually listens to for driving the robot
    collision_monitor_node = Node(
        package='nav2_collision_monitor',
        executable='collision_monitor',
        name='collision_monitor',
        output='screen',
        parameters=[configured_params],
    )

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': LIFECYCLE_NODES,
        }]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz_navigation',
        output='screen',
        arguments=['-d', DEFAULT_RVIZ_CONFIG],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    ld = LaunchDescription()
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(localization_launch)
    ld.add_action(controller_server_node)
    ld.add_action(planner_server_node)
    ld.add_action(behavior_server_node)
    ld.add_action(bt_navigator_node)
    ld.add_action(waypoint_follower_node)
    ld.add_action(velocity_smoother_node)
    ld.add_action(collision_monitor_node)
    ld.add_action(lifecycle_manager_node)
    ld.add_action(rviz_node)
    return ld
