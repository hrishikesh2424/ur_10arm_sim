#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    
    # Declare arguments
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation clock if true",
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "gui",
            default_value="true",
            description="Start Gazebo with GUI",
        )
    )

    # Initialize Arguments
    use_sim_time = LaunchConfiguration("use_sim_time")
    gui = LaunchConfiguration("gui")

    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("ur_yt_sim"), "urdf", "ur10_camera_3f_gripper.urdf.xacro"]
            ),
        ]
    )
    
    robot_description = {"robot_description": robot_description_content}

    # Robot State Publisher Node
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description, {"use_sim_time": use_sim_time}],
    )

    # Gazebo launch
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])]
        ),
        launch_arguments={
            "verbose": "false",
            "pause": "true",
            "gui": gui,
        }.items(),
    )

    # Spawn robot
    spawn_entity_node = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-topic", "robot_description",
            "-entity", "ur10_robot",
            "-x", "0.0",
            "-y", "0.0",
            "-z", "0.01",
        ],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Load Joint State Broadcaster
    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Load UR10 Arm Controller
    load_ur10_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["ur10_controller", "--controller-manager", "/controller_manager"],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Load Gripper Controller (if configured)
    load_gripper_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller", "--controller-manager", "/controller_manager"],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Delay start of robot controller after joint_state_broadcaster
    delay_ur10_controller_after_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_ur10_controller],
        )
    )

    # Delay start of gripper controller after arm controller
    delay_gripper_controller_after_ur10_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_ur10_controller,
            on_exit=[load_gripper_controller],
        )
    )

    # RViz
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("ur_yt_sim"), "rviz", "config_ur10_robotiq.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    nodes_to_start = [
        gazebo,
        robot_state_publisher_node,
        spawn_entity_node,
        load_joint_state_broadcaster,
        delay_ur10_controller_after_joint_state_broadcaster,
        delay_gripper_controller_after_ur10_controller,
        rviz_node,
    ]

    return LaunchDescription(declared_arguments + nodes_to_start)