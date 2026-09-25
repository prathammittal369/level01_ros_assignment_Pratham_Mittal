#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_prefix
from launch.actions import ExecuteProcess

def generate_launch_description():

    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    pkg_testbed_gazebo = get_package_share_directory('testbed_gazebo')

    # grabbing the install dir for testbed_description
    # this way i don't have to manually symlink/copy the package for gazebo to find it
    description_package_name = "testbed_description"
    install_dir = get_package_prefix(description_package_name)

    # need this so gazebo knows where to look for our custom models (the models folder in testbed_gazebo)
    gazebo_models_path = os.path.join(pkg_testbed_gazebo, 'models')
    # os.environ["GAZEBO_MODEL_PATH"] = gazebo_models_path  (old way, not using this line anymore)

    if 'GAZEBO_MODEL_PATH' in os.environ:
        os.environ['GAZEBO_MODEL_PATH'] =  os.environ['GAZEBO_MODEL_PATH'] + ':' + install_dir + '/share' + ':' + gazebo_models_path
    else:
        os.environ['GAZEBO_MODEL_PATH'] =  install_dir + "/share" + ':' + gazebo_models_path

    if 'GAZEBO_PLUGIN_PATH' in os.environ:
        os.environ['GAZEBO_PLUGIN_PATH'] = os.environ['GAZEBO_PLUGIN_PATH'] + ':' + install_dir + '/lib'
    else:
        os.environ['GAZEBO_PLUGIN_PATH'] = install_dir + '/lib'

    print("GAZEBO MODELS PATH=="+str(os.environ["GAZEBO_MODEL_PATH"]))
    print("GAZEBO PLUGINS PATH=="+str(os.environ["GAZEBO_PLUGIN_PATH"]))

    # bringing up the actual gazebo simulator
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py'),
        ),
    )    

    return LaunchDescription([
        DeclareLaunchArgument(
          'world',
          default_value=[os.path.join(pkg_testbed_gazebo, 'worlds', 'testbed_playground.world'), ''],
          description='SDF world file'),
        gazebo,
    ])
