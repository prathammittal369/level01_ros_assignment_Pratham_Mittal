import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node

# entry point function, ros2 launch calls this for us
def generate_launch_description():

    # ---- basic settings for this launch file ----
    urdf_file = 'testbed.xacro'
    package_description = "testbed_description"

    print("Fetching URDF ==>")  # just a print so i can see it's actually finding the file when i run it
    robot_desc_path = os.path.join(
        get_package_share_directory(package_description), "urdf", urdf_file)

    # this node publishes the robot's tf tree from the urdf/xacro
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher_node',
        emulate_tty=True,
        parameters=[{'use_sim_time': True, 
                     'robot_description': Command(['xacro ', robot_desc_path])}],
        output="screen"
    )

    # publishes joint states so we can see the wheels etc move in rviz
    joint_state_controller_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher'
            # parameters=[
            #     {'use_sim_time': LaunchConfiguration('use_sim_time')}
            # ] # left this commented out - tried adding use_sim_time here but it kept
              # erroring out (something about it being set twice), so skipping it for now
    )
    
    # path to the rviz config so it opens with the right displays already set up
    rviz_config_dir = os.path.join(
        get_package_share_directory(package_description),
        'rviz',
        'testbed_barebones.rviz')
    
    rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz_node',
            parameters=[{'use_sim_time': True}],
            arguments=['-d', rviz_config_dir]
    )

    # bundle everything up and hand it back to ros2 launch
    return LaunchDescription([            
            robot_state_publisher_node,
            joint_state_controller_node,
            rviz_node,
    ])
