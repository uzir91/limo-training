from os.path import join
from os import popen, environ
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, TimerAction, SetEnvironmentVariable
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.descriptions import ParameterFile

def normalize_namespace(ns: str, add_trailing: bool = True) -> str:
    stripped = ns.strip('/')
    if not stripped:
        return ''
    return stripped + '/' if add_trailing else stripped

def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=generate_context)
    ])

def generate_context(context, *args, **kwargs):
    # --- Resolve arguments ---
    GetArgument = context.launch_configurations.get
    FindPackage = get_package_share_directory

    limo_description_pkg = FindPackage('limo_description')

    rviz_config = join(limo_description_pkg, 'rviz', 'description.rviz')
    xacro_config = join(limo_description_pkg, 'urdf', 'assembly.xacro')

    namespace = GetArgument('namespace', 'limo')
    gpu = GetArgument('gpu', 'default').lower()

    simulation = GetArgument('simulation', 'false').lower() in ['true', '1', 'yes']
    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']
    joint_state = GetArgument('joint_state', 'true').lower() in ['true', '1', 'yes']
    joint_state_gui = GetArgument('joint_state_gui', 'true').lower() in ['true', '1', 'yes']

    controller_manager_path = GetArgument('controller_manager_path', join(limo_description_pkg, 'config', 'controller_manager.yaml'))
    ros2_control_path = GetArgument('ros2_control_path', join(limo_description_pkg, 'urdf', 'ros2_control.xacro'))

    gpu_environment = []
    actions = []

    if gpu == 'nvidia':
        gpu_environment = [
            SetEnvironmentVariable(
                name='__NV_PRIME_RENDER_OFFLOAD',
                value='1',
            ),
            SetEnvironmentVariable(
                name='__GLX_VENDOR_LIBRARY_NAME',
                value='nvidia',
            ),
            SetEnvironmentVariable(
                name='__VK_LAYER_NV_optimus',
                value='NVIDIA_only',
            ),
        ]

    else:
        gpu_environment = [
            SetEnvironmentVariable(
                name='DRI_PRIME',
                value='1',
            ),
        ]

    robot_description = popen(f"xacro {xacro_config} namespace:={normalize_namespace(namespace, False)} controller_manager_path:={controller_manager_path} ros2_control_path:={ros2_control_path}").read()
    actions.append(
        Node(
            namespace = normalize_namespace(namespace, False),
            package ='robot_state_publisher',
            executable ='robot_state_publisher',
            output ='screen',
            parameters = [{
                'robot_description': robot_description,
                'use_sim_time': simulation,
            }],
        )
    )

    if joint_state:
        if joint_state_gui:
            actions.append(
                Node(
                    namespace = normalize_namespace(namespace, False),
                    package='joint_state_publisher_gui',
                    executable='joint_state_publisher_gui',
                    output='screen',
                    parameters = [{
                        'use_sim_time': simulation,
                    }],
                ),
            )
        else:
            actions.append(
                Node(
                    namespace = normalize_namespace(namespace, False),
                    package='joint_state_publisher',
                    executable='joint_state_publisher',
                    output='screen',
                    parameters = [{
                        'use_sim_time': simulation,
                    }],
                ),
            )

    # Rviz
    if rviz:
        actions.append(
            GroupAction(
                scoped=True,
                forwarding=False,
                actions=[
                    *gpu_environment,
                    Node(
                        namespace=normalize_namespace(namespace, False),
                        package='rviz2',
                        executable='rviz2',
                        output='screen',
                        parameters=[
                            {
                                'use_sim_time': simulation,
                            },
                        ],
                        arguments=[
                            '-d',
                            rviz_config,
                        ],
                        remappings=[
                            ('/goal_pose', 'goal_pose'),
                            ('/clicked_point', 'clicked_point'),
                            ('/initialpose', 'initialpose'),
                        ],
                    )
                ],
            )
        )

    return actions