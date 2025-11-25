#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    
    # Declare arguments
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_package",
            default_value="ur_yt_sim",
            description="Description package with robot URDF/XACRO files.",
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value="ur10_camera_3f_gripper.urdf.xacro",
            description="URDF/XACRO description file with the robot.",
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value='""',
            description="Prefix of the joint names, useful for multi-robot setup.",
        )
    )

    # Initialize Arguments
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    prefix = LaunchConfiguration("prefix")

    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare(description_package), "urdf", description_file]
            ),
            " ",
            "prefix:=",
            prefix,
        ]
    )
    
    robot_description = {"robot_description": robot_description_content}

    # RViz configuration file
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("ur_yt_sim"), "rviz", "view_ur10_camera.rviz"]
    )

    # Robot State Publisher Node
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    # Joint State Publisher GUI Node
    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
    )

    # RViz Node
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    nodes_to_start = [
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node,
    ]

    return LaunchDescription(declared_arguments + nodes_to_start)