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

from nav2_common.launch import ReplaceString, RewrittenYaml


# from launch import LaunchDescription
# from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription
# from launch.launch_description_sources import PythonLaunchDescriptionSource
# from launch_ros.actions import Node

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

    namespace = GetArgument('namespace', 'limo')
    # namespace2 = GetArgument('namespace2', 'qwe')

    simulation = GetArgument('simulation', 'false').lower() in ['true', '1', 'yes']
    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']
    gui = GetArgument('gui', 'false').lower() in ['true', '1', 'yes']
    gpu = GetArgument('gpu', 'default').lower()
    rviz_config = GetArgument('rviz_config', 'bringup.rviz')
    world_config = GetArgument('world_config', 'limo_world.sdf')
    simulation_control_config = GetArgument('simulation_control_config', 'simulation_control.yaml')
    hardware_control_config = GetArgument('hardware_control_config', 'hardware_control.yaml')

    limo_bringup_pkg = FindPackage('limo_bringup')
    ros_gz_pkg = FindPackage('ros_gz_sim')
    gazebo_pkg = FindPackage('gazebo_ros')
    world_path = join(limo_bringup_pkg, 'worlds', world_config)
    rviz_path = join(limo_bringup_pkg, 'rviz', rviz_config)
    xacro_path = join(limo_bringup_pkg, 'description', 'urdf', 'assembly.xacro')
    control_path = join(limo_bringup_pkg, 'config', simulation_control_config if simulation else hardware_control_config)
    ros_gz_launch = join(ros_gz_pkg, 'launch', 'gz_sim.launch.py')
    gazebo_launch = join(gazebo_pkg, 'launch', 'gazebo.launch.py')

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

    elif gpu == 'amd':
        gpu_environment = [
            SetEnvironmentVariable(
                name='DRI_PRIME',
                value='1',
            ),
        ]

    robot_description = popen(f"xacro {xacro_path} prefix:={normalize_namespace(namespace, False)}_ namespace:={normalize_namespace(namespace, False)} simulation:={simulation} control_path:={control_path}").read()
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

    if simulation:
        # Gazebo Sim
        gz_sim_node = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                ros_gz_launch
            ),
            launch_arguments={
                'gz_args': f'-r -v 3 {world_path}',
            }.items(),
        )
        if gpu_environment:
            actions.append(
                GroupAction(
                    scoped=True,
                    actions=[
                        *gpu_environment,
                        gz_sim_node,
                    ],
                )
            )
        else:
            actions.append(gz_sim_node)

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
    else:
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
                    control_path
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
            ],
            output='screen',
            parameters=[{'use_sim_time': True}]
        )
    )

    # Rviz
    if rviz:
        rviz_node = Node(
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
                rviz_path,
            ],
            remappings=[
                ('/goal_pose', 'goal_pose'),
                ('/clicked_point', 'clicked_point'),
                ('/initialpose', 'initialpose'),
            ],
        )
        if gpu_environment:
            actions.append(
                GroupAction(
                    scoped=True,
                    actions=[
                        *gpu_environment,
                        rviz_node,
                    ],
                )
            )
        else:
            actions.append(rviz_node)


    # TF Delay
    # actions.append(
    #     Node(
    #         namespace = normalize_namespace(namespace, False),
    #         package='tf_relay',
    #         executable='tf_relay_node',
    #         output='screen',
    #         parameters=[
    #             {
    #                 # 'tf_prefix': normalize_namespace(namespace, True)
    #             },
    #         ],
    #         remappings=[('/tf_in', 'tf'),
    #                     ('/tf_out', '/tf'),
    #                     ('/tf_static_in', 'tf_static'),
    #                     ('/tf_static_out', '/tf_static')]
    #     )
    # )

    return actions