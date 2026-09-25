#!/usr/bin/python3
# -*- coding: utf-8 -*-
import random

from launch_ros.actions import Node
from launch import LaunchDescription


# ros2 launch looks for this function automatically, learned that the hard way lol
def generate_launch_description():


    # where i want the robot to spawn in the world
    # order is x, y, z
    position = [0.0, 5.0, 0.0]
    # and this is roll, pitch, yaw (radians i think, not 100% sure)
    orientation = [0.0, 0.0, 0.0]
    # just naming the robot entity here
    robot_base_name = "testbed"


    entity_name = robot_base_name#+"-"+str(int(random.random()*100000))
    # ^ was going to add a random suffix so i could spawn multiple robots
    # but didn't need it for this assignment, leaving it commented for now

    # this node actually spawns the robot into gazebo using the urdf on /robot_description
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_entity',
        output='screen',
        arguments=['-entity',
                   entity_name,
                   '-x', str(position[0]), '-y', str(position[1]
                                                     ), '-z', str(position[2]),
                   '-R', str(orientation[0]), '-P', str(orientation[1]
                                                        ), '-Y', str(orientation[2]),
                   '-topic', '/robot_description'
                   ]
    )

 

    # gotta return a LaunchDescription with all the nodes/actions in it
    return LaunchDescription(
        [
            spawn_robot,
        ]
    )
