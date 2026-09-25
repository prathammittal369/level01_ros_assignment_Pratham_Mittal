#!/usr/bin/env python3
"""
map_loader.launch.py

This is step 4 of the assignment. All this file does is bring up the
nav2_map_server node by itself (no AMCL, no nav stack, nothing else) so I
can just check in rviz that the map is loading correctly before adding
more stuff on top of it.

how to run it:
    ros2 launch testbed_navigation map_loader.launch.py
    (or point it at a different map like this)
    ros2 launch testbed_navigation map_loader.launch.py \
        map:=/absolute/path/to/other_map.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# quick note: the map.yaml that came with testbed_bringup was originally
# pointing to a pgm file that didn't even exist (typo'd path), and on top of
# that the CMakeLists.txt wasn't installing the maps/ folder at all, so it
# would never be found anyway. Fixed both of those (see BUGS_AND_FIXES.md
# if curious), so this now just points at the map that actually gets
# installed properly.
DEFAULT_MAP = os.path.join(
    get_package_share_directory('testbed_bringup'), 'maps', 'testbed_world.yaml'
)


def generate_launch_description():

    map_yaml_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')

    declare_map_cmd = DeclareLaunchArgument(
        'map',
        default_value=DEFAULT_MAP,
        description='Full path to the map yaml file to load')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically bring the map_server node up to the active state')

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

    # map_server is a lifecycle node (had to look this up), meaning it just
    # sits there "unconfigured" unless something else tells it to configure
    # and activate itself - that's what the lifecycle manager below does
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map_server',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': ['map_server'],
        }]
    )

    ld = LaunchDescription()
    ld.add_action(declare_map_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(map_server_node)
    ld.add_action(lifecycle_manager_node)
    return ld
