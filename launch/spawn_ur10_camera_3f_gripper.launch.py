#!/usr/bin/env python3
"""
Launch file for UR10 + Camera + Robotiq 3F Gripper in Gazebo
This file orchestrates starting all necessary nodes for simulation
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """
    Main function that returns the complete launch configuration
    """
    
    # =============================================================================
    # SECTION 1: DECLARE LAUNCH ARGUMENTS
    # =============================================================================
    # These are parameters you can change when launching
    # Example: ros2 launch ur_yt_sim spawn_ur10_camera_3f_gripper.launch.py launch_rviz:=false
    
    declared_arguments = []
    
    # Robot type (UR3, UR5, UR10, etc.)
    declared_arguments.append(
        DeclareLaunchArgument(
            "ur_type",
            default_value="ur10",
            description="Type/series of used UR robot.",
        )
    )
    
    # Use fake hardware (for simulation)
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="true",
            description="Start robot with fake hardware.",
        )
    )
    
    # Use simulation time from Gazebo
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation clock",
        )
    )
    
    # Prefix for joint/link names (usually empty)
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value='""',
            description="Prefix of joint and link names",
        )
    )
    
    # Whether to launch RViz
    declared_arguments.append(
        DeclareLaunchArgument(
            "launch_rviz",
            default_value="true",
            description="Launch RViz",
        )
    )
    
    # Which Gazebo world to load
    declared_arguments.append(
        DeclareLaunchArgument(
            "world",
            default_value="empty.world",
            description="Gazebo world file",
        )
    )

    # =============================================================================
    # SECTION 2: GET LAUNCH ARGUMENT VALUES
    # =============================================================================
    # Convert arguments to usable variables
    
    ur_type = LaunchConfiguration("ur_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    use_sim_time = LaunchConfiguration("use_sim_time")
    prefix = LaunchConfiguration("prefix")
    launch_rviz = LaunchConfiguration("launch_rviz")
    world = LaunchConfiguration("world")

    # =============================================================================
    # SECTION 3: GENERATE ROBOT DESCRIPTION (URDF)
    # =============================================================================
    # This runs xacro to convert your .xacro file to URDF
    # The URDF describes the robot's physical structure
    
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),  # Find xacro executable
            " ",
            PathJoinSubstitution([
                FindPackageShare("ur_yt_sim"),  # Your package
                "urdf",
                "ur10_camera_3f_gripper.urdf.xacro"  # Your URDF file
            ]),
            " ",
            # Pass arguments to xacro
            "ur_type:=", ur_type,
            " ",
            "use_fake_hardware:=", use_fake_hardware,
            " ",
            "prefix:=", prefix,
            " ",
            "name:=", "ur10",
        ]
    )
    
    robot_description = {"robot_description": robot_description_content}

    # =============================================================================
    # SECTION 4: LOAD CONTROLLER CONFIGURATION
    # =============================================================================
    # Path to your controller YAML file
    
    robot_controllers = PathJoinSubstitution([
        FindPackageShare("ur_yt_sim"),
        "config",
        "ur10_camera_3f_controllers.yaml",
    ])

    # =============================================================================
    # SECTION 5: ROBOT STATE PUBLISHER NODE
    # =============================================================================
    # This node publishes the robot's state (TF transforms, joint states)
    # Required for RViz and other nodes to know where the robot is
    
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description, {"use_sim_time": use_sim_time}],
    )

    # =============================================================================
    # SECTION 6: START GAZEBO
    # =============================================================================
    # Launch Gazebo simulation environment
    
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")
    
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "verbose": "false",  # Don't show detailed output
            "pause": "false",    # Start unpaused
            "world": PathJoinSubstitution([
                FindPackageShare("ur_yt_sim"),
                "worlds",
                world  # World file from arguments
            ])
        }.items(),
    )

    # =============================================================================
    # SECTION 7: SPAWN ROBOT IN GAZEBO
    # =============================================================================
    # This takes the robot description and places it in the Gazebo world
    
    spawn_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-topic", "robot_description",  # Get URDF from this topic
            "-entity", "ur10_camera_3f_gripper",  # Name of robot in Gazebo
            "-x", "0.0",  # X position in world
            "-y", "0.0",  # Y position in world
            "-z", "0.1",  # Z position in world (slightly above ground)
        ],
        output="screen",
    )

    # =============================================================================
    # SECTION 8: SPAWN CONTROLLERS
    # =============================================================================
    # These nodes start the ROS2 controllers for the robot
    
    # Joint State Broadcaster - publishes joint states
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    # UR10 Arm Controller - controls the 6 arm joints
    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "scaled_joint_trajectory_controller",  # Standard UR controller name
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    # Robotiq 3F Gripper Controller - controls the gripper
    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "robotiq_3f_gripper_controller",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    # =============================================================================
    # SECTION 9: SEQUENTIAL CONTROLLER STARTUP
    # =============================================================================
    # Controllers must start in order:
    # 1. Joint state broadcaster FIRST
    # 2. Arm controller SECOND (after joint state broadcaster exits)
    # 3. Gripper controller THIRD (after arm controller exits)
    
    delay_arm_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,  # Wait for this to finish
            on_exit=[arm_controller_spawner],  # Then start this
        )
    )

    delay_gripper_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_controller_spawner,  # Wait for this to finish
            on_exit=[gripper_controller_spawner],  # Then start this
        )
    )

    # =============================================================================
    # SECTION 10: START RVIZ (OPTIONAL)
    # =============================================================================
    # RViz for visualization - only if launch_rviz:=true
    
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare("ur_yt_sim"),
        "rviz",
        "view_ur10_camera_3f_gripper.rviz"  # RViz config file
    ])
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(launch_rviz),  # Only launch if argument is true
    )
    
    # Delay RViz start by 3 seconds (let Gazebo initialize first)
    delay_rviz = TimerAction(
        period=3.0,
        actions=[rviz_node],
    )

    # =============================================================================
    # SECTION 11: COMBINE ALL NODES INTO LAUNCH DESCRIPTION
    # =============================================================================
    # The order here matters - nodes will start in this sequence
    
    nodes = [
        gazebo,                              # 1. Start Gazebo
        robot_state_publisher_node,          # 2. Start robot state publisher
        spawn_entity,                        # 3. Spawn robot in Gazebo
        joint_state_broadcaster_spawner,     # 4. Start joint state broadcaster
        delay_arm_controller,                # 5. Wait, then start arm controller
        delay_gripper_controller,            # 6. Wait, then start gripper controller
        delay_rviz,                          # 7. Wait 3s, then start RViz
    ]

    return LaunchDescription(declared_arguments + nodes)


# =============================================================================
# USAGE EXAMPLES:
# =============================================================================
# Basic launch:
#   ros2 launch ur_yt_sim spawn_ur10_camera_3f_gripper.launch.py
#
# Without RViz:
#   ros2 launch ur_yt_sim spawn_ur10_camera_3f_gripper.launch.py launch_rviz:=false
#
# With custom world:
#   ros2 launch ur_yt_sim spawn_ur10_camera_3f_gripper.launch.py world:=table.world
#
# Different UR type:
#   ros2 launch ur_yt_sim spawn_ur10_camera_3f_gripper.launch.py ur_type:=ur5
# =============================================================================