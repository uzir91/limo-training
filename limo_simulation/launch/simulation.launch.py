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

    limo_simulation_pkg = FindPackage('limo_simulation')
    limo_description_pkg = FindPackage('limo_description')

    limo_description_launch = join(limo_description_pkg, 'launch', 'description.launch.py')
    rviz_config = join(limo_simulation_pkg, 'rviz', 'simulation.rviz')

    namespace = GetArgument('namespace', 'limo')
    world = GetArgument('world', 'limo_world.sdf')
    gpu = GetArgument('gpu', 'default').lower()

    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']

    world_path = GetArgument('world_path', join(limo_simulation_pkg, 'worlds', world))
    controller_manager_path = GetArgument('controller_manager_path', join(limo_simulation_pkg, 'config', 'controller_manager.yaml'))
    ros2_control_path = GetArgument('ros2_control_path', join(limo_simulation_pkg, 'urdf', 'ros2_control.xacro'))

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
                        'simulation': f'True',
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

    # Gazebo Sim
    actions.append(
        GroupAction(
            scoped=True,
            forwarding=False,
            actions=[
                *gpu_environment,
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        join(FindPackage('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
                    ),
                    launch_arguments={
                        'gz_args': f'-r -v 3 {world_path}',
                    }.items(),
                )
            ],
        )
    )

    # Gazebo Spawn
    actions.append(
        Node(
            namespace = normalize_namespace(namespace, False),
            package='ros_gz_sim',
            executable='create',
            output='screen',
            arguments=[
                '-topic', '/'+normalize_namespace(namespace, True)+'robot_description',
                '-name', normalize_namespace(namespace, False),
                # '-allow_renaming', 'true',
            ],
        )
    )

    # Gazebo Bridge
    actions.append(
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                f'/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',

                f'/{normalize_namespace(namespace, True)}imu/data@sensor_msgs/msg/Imu[ignition.msgs.IMU',
                f'/{normalize_namespace(namespace, True)}scan/data@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
                f'/{normalize_namespace(namespace, True)}camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
                f'/{normalize_namespace(namespace, True)}camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
                f'/{normalize_namespace(namespace, True)}camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
                f'/{normalize_namespace(namespace, True)}camera/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
            ],
            output='screen',
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
            parameters=[{'use_sim_time': True}]
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
                                'use_sim_time': True,
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