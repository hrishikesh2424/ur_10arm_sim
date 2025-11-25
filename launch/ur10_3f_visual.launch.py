from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    # Path to the URDF/XACRO file
    pkg_share = get_package_share_directory('ur_yt_sim')
    default_model_path = os.path.join(pkg_share, 'urdf', 'ur10_3f_visual.urdf.xacro')

    # Launch arguments
    model_arg = DeclareLaunchArgument(
        name='model',
        default_value=default_model_path,
        description='Absolute path to URDF/XACRO file'
    )

    # Generate robot_description using Xacro
    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('model')]),
        value_type=str
    )

    # Robot State Publisher Node
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description
        }]
    )

    # Joint State Publisher GUI
    jsp_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui'
    )

    # RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen'
    )

    return LaunchDescription([
        model_arg,
        rsp_node,
        jsp_gui,
        rviz_node
    ])
