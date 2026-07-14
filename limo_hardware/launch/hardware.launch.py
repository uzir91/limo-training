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

    limo_hardware_pkg = FindPackage('limo_hardware')
    limo_description_pkg = FindPackage('limo_description')

    limo_description_launch = join(limo_description_pkg, 'launch', 'description.launch.py')
    rviz_config = join(limo_hardware_pkg, 'rviz', 'hardware.rviz')

    namespace = GetArgument('namespace', 'limo')
    gpu = GetArgument('gpu', 'default').lower()

    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']

    controller_manager_path = GetArgument('controller_manager_path', join(limo_hardware_pkg, 'config', 'controller_manager.yaml'))
    ros2_control_path = GetArgument('ros2_control_path', join(limo_hardware_pkg, 'urdf', 'ros2_control.xacro'))

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

    # Limo description
    actions.append(
        GroupAction(
            scoped=True,
            forwarding=False,
            actions=[
                *gpu_environment,
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        limo_description_launch
                    ),
                    launch_arguments={
                        'namespace': f'{namespace}',
                        'gpu': f'{gpu}',
                        'simulation': f'False',
                        'rviz': f'False',
                        'joint_state': f'False',
                        'joint_state_gui': f'False',
                        'controller_manager_path': f'{controller_manager_path}',
                        'ros2_control_path': f'{ros2_control_path}',
                    }.items(),
                )
            ],
        )
    )

    # Controller manager
    actions.append(
        Node(
            namespace = normalize_namespace(namespace, False),
            package='controller_manager',
            executable='ros2_control_node',
            output='screen',
            parameters=[
                {
                    'use_sim_time': False
                },
                controller_manager_path
            ],
            remappings=[('~/robot_description', '/'+normalize_namespace(namespace, True)+'robot_description')]
        )
    )

    # Controller Spawn
    actions.append(
        Node(
            namespace = normalize_namespace(namespace, False),
            package='controller_manager',
            executable='spawner',
            arguments=[
                'joint_state_broadcaster',
                'diff_drive_controller',
                "--controller-manager-timeout", "120",
                "--service-call-timeout", "120",
                "--switch-timeout", "120",
            ],
            output='screen',
            parameters=[{'use_sim_time': False}]
        )
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
                                'use_sim_time': False,
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