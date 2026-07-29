from os.path import join, exists
from os import popen, environ
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, TimerAction, SetEnvironmentVariable
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node, PushRosNamespace, ComposableNodeContainer, LoadComposableNodes
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.descriptions import ParameterFile, ComposableNode

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
    ros_gz_sim_pkg = FindPackage('ros_gz_sim')

    limo_description_launch = join(limo_description_pkg, 'launch', 'description.launch.py')
    ros_gz_sim_launch = join(ros_gz_sim_pkg, 'launch', 'gz_sim.launch.py')

    namespace = GetArgument('namespace', 'limo')
    gpu = GetArgument('gpu', 'default').lower()
    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']
    limo_base_filename = GetArgument('limo_base_filename', 'limo_base.yaml')
    lidar_filename = GetArgument('lidar_filename', 'lidar.yaml')
    camera_filename = GetArgument('camera_filename', 'camera.yaml')
    controller_manager_filename = GetArgument('controller_manager_filename', 'controller_manager.yaml')
    ros2_control_filename = GetArgument('ros2_control_filename', 'ros2_control.xacro')
    joy_filename = GetArgument('joy_filename', 'joy.yaml')
    teleop_twist_filename = GetArgument('teleop_twist_filename', 'teleop_twist.yaml')
    imu_filter_filename = GetArgument('imu_filter_filename', 'imu_filter.yaml')
    safety_imu_filename = GetArgument('safety_imu_filename', 'safety_imu.yaml')
    safety_hardware_filename = GetArgument('safety_hardware_filename', 'safety_hardware.yaml')
    twist_mux_filename = GetArgument('twist_mux_filename', 'twist_mux.yaml')
    rviz_filename = GetArgument('rviz_filename', 'hardware.rviz')

    limo_base_path = GetArgument('limo_base_path', join(limo_hardware_pkg, 'config', namespace, limo_base_filename))
    lidar_path = GetArgument('lidar_path', join(limo_hardware_pkg, 'config', namespace, lidar_filename))
    camera_path = GetArgument('camera_path', join(limo_hardware_pkg, 'config', namespace, camera_filename))
    controller_manager_path = GetArgument('controller_manager_path', join(limo_hardware_pkg, 'config', namespace, controller_manager_filename))
    ros2_control_path = GetArgument('ros2_control_path', join(limo_hardware_pkg, 'urdf', ros2_control_filename))
    joy_path = GetArgument('joy_path', join(limo_hardware_pkg, 'config', namespace, joy_filename))
    teleop_twist_path = GetArgument('teleop_twist_path', join(limo_hardware_pkg, 'config', namespace, teleop_twist_filename))
    imu_filter_path = GetArgument('imu_filter_path', join(limo_hardware_pkg, 'config', namespace, imu_filter_filename))
    safety_imu_path = GetArgument('safety_imu_path', join(limo_hardware_pkg, 'config', namespace, safety_imu_filename))
    safety_hardware_path = GetArgument('safety_hardware_path', join(limo_hardware_pkg, 'config', namespace, safety_hardware_filename))
    twist_mux_path = GetArgument('twist_mux_path', join(limo_hardware_pkg, 'config', namespace, twist_mux_filename))
    rviz_path = GetArgument('rviz_path', join(limo_hardware_pkg, 'rviz', rviz_filename))

    if not exists(limo_base_path):
        limo_base_path = join(limo_hardware_pkg, 'config', 'limo_base.yaml')
    if not exists(lidar_path):
        lidar_path = join(limo_hardware_pkg, 'config', 'lidar.yaml')
    if not exists(camera_path):
        camera_path = join(limo_hardware_pkg, 'config', 'camera.yaml')
    if not exists(controller_manager_path):
        controller_manager_path = join(limo_hardware_pkg, 'config', 'controller_manager.yaml')
    if not exists(ros2_control_path):
        ros2_control_path = join(limo_hardware_pkg, 'urdf', 'ros2_control.xacro')
    if not exists(joy_path):
        joy_path = join(limo_hardware_pkg, 'config', 'joy.yaml')
    if not exists(teleop_twist_path):
        teleop_twist_path = join(limo_hardware_pkg, 'config', 'teleop_twist.yaml')
    if not exists(imu_filter_path):
        imu_filter_path = join(limo_hardware_pkg, 'config', 'imu_filter.yaml')
    if not exists(safety_imu_path):
        safety_imu_path = join(limo_hardware_pkg, 'config', 'safety_imu.yaml')
    if not exists(safety_hardware_path):
        safety_hardware_path = join(limo_hardware_pkg, 'config', 'safety_hardware.yaml')
    if not exists(twist_mux_path):
        twist_mux_path = join(limo_hardware_pkg, 'config', 'twist_mux.yaml')
    if not exists(rviz_path):
        rviz_path = join(limo_hardware_pkg, 'rviz', 'simulation.rviz')

    gpu_environment = []
    actions = []
    components = []

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
                        'namespace': f'{join(namespace)}',
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

    # Limo base
    actions.append(
        Node(
            package='limo_base',
            executable='limo_base',
            namespace=join(namespace),
            name='limo_base_node',
            output='screen',
            parameters=[
                limo_base_path,
                {
                    'use_sim_time': False,
                    'odom_frame': join(namespace, 'odom'),
                    'base_frame': join(namespace, 'base_footprint'),
                    'imu_frame': join(namespace, 'imu_link'),
                },
            ],
            remappings=[
                ('/cmd_vel', join('/', namespace, 'diff_drive_controller/cmd_vel_unstamped')),
                ('odom', join('/', namespace, 'diff_drive_controller/odom')),
                ('/imu', join('/', namespace, 'imu/data')),
                ('/limo_status', join('/', namespace, 'status')),
            ]
        )
    )

    # Lidar
    actions.append(
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            namespace=join(namespace),
            name='lidar_node',
            output='screen',
            parameters=[
                lidar_path,
                {
                    'use_sim_time': False,
                    'frame_id': join(namespace, 'lidar_link'),
                },
            ],
            remappings=[
                ('scan', 'scan/data'),
            ]
        )
    )

    # Depth camera
    components.append(
        ComposableNode(
            package="orbbec_camera",
            plugin="orbbec_camera::OBCameraNodeDriver",
            # executable="orbbec_camera_node",
            namespace=join(namespace, 'camera'),
            name='camera_node',
            # output='screen',
            parameters=[
                camera_path,
                {
                    'use_sim_time': False,
                    'color_optical_frame_id': join(namespace, 'image_link'),
                },
            ],
            remappings=[
                ('depth_registered/points', 'points'),
                ('color/image_raw', 'image'),
            ]
        )
    )

    # Controller manager
    actions.append(
        Node(
            package='controller_manager',
            executable='ros2_control_node',
            namespace=join(namespace),
            # name='controller_manager',
            output='screen',
            parameters=[
                controller_manager_path,
                {
                    'use_sim_time': False
                },
            ],
            remappings=[
                ('~/robot_description', join('/', namespace, 'robot_description')),
                ('diff_drive_controller/odom', join('/', namespace, 'odom')),
            ]
        )
    )

    # Controller Spawn
    actions.append(
        Node(
            package='controller_manager',
            executable='spawner',
            namespace=join(namespace),
            name='controller_manager_spawner_node',
            output='screen',
            arguments=[
                'joint_state_broadcaster',
                'diff_drive_controller',
                "--controller-manager-timeout", "120",
                "--service-call-timeout", "120",
                "--switch-timeout", "120",
            ],
            parameters=[
                {'use_sim_time': False},
            ],
            remappings=[
            ]
        )
    )

    # Joy
    actions.append(
        Node(
            package='joy',
            # plugin='joy::Joy',
            executable='joy_node',
            namespace=join(namespace),
            name='joy_component',
            parameters=[
                joy_path,
                {'use_sim_time': False},
            ]
        ),
    )


    # Teleop Twist Joy
    actions.append(
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            namespace=join(namespace),
            name='teleop_twist_node',
            parameters=[
                teleop_twist_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('cmd_vel', 'joy/cmd_vel'),
            ]
        ),
    )

    # IMU Filter
    actions.append(
        Node(
            package='imu_complementary_filter',
            executable='complementary_filter_node',
            namespace=join(namespace),
            name='imu_filter_node',
            output='screen',
            parameters=[
                imu_filter_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('imu/data_raw', 'imu/data'),
                ('imu/data', 'imu/filtering'),
            ],
        )
    )

    # IMU safety
    actions.append(
        Node(
            package='safety_imu',
            # plugin='safety_imu::SafetyImuComponent',
            executable='safety_imu_node',
            namespace=join(namespace),
            name='safety_imu_component',
            parameters=[
                safety_imu_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('imu/input', 'imu/filtering'),
                ('imu/output', 'imu/filtered'),
                ('odom/input', 'diff_drive_controller/odom'),
                ('odom/output', 'odom/filtered'),
                ('error', 'safety_imu/error'),
            ],
        )
    )

    # Safety Hardware
    actions.append(
        Node(
            package='safety_hardware',
            # plugin='safety_hardware::SafetyHardwareComponent',
            executable='safety_hardware_node',
            namespace=join(namespace),
            name='safety_hardware_component',
            parameters=[
                safety_hardware_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('error', 'hardware/error'),
            ],
            # extra_arguments=[
            #     {'use_intra_process_comms': False},
            # ],
        )
    )

    # Twist Mux
    actions.append(
        Node(
            package='twist_mux',
            executable='twist_mux',
            namespace=join(namespace),
            name='twist_mux_node',
            output='screen',
            parameters=[
                twist_mux_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('cmd_vel_out', 'diff_drive_controller/cmd_vel_unstamped'),
            ]
        ),
    )

    # # Lifecycle Manager
    # components.append(
    #     ComposableNode(
    #         package='nav2_lifecycle_manager',
    #         plugin='nav2_lifecycle_manager::LifecycleManager',
    #         namespace=join(namespace),
    #         name='lifecycle_manager_hardware',
    #         parameters=[
    #             {
    #                 'use_sim_time': False,
    #                 'autostart': True,
    #                 'node_names': [
    #                 ],
    #                 'bond_timeout': 0.0,
    #             },
    #         ],
    #     ),
    # )

    # Rviz
    if rviz:
        actions.append(
            GroupAction(
                scoped=True,
                forwarding=False,
                actions=[
                    *gpu_environment,
                    Node(
                        namespace=join(namespace),
                        package='rviz2',
                        executable='rviz2',
                        output='screen',
                        parameters=[
                            {'use_sim_time': False},
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
                ],
            )
        )

    # Composoble Container
    actions.append(
        Node(
            package='rclcpp_components',
            executable='component_container_isolated',
            name='component_container_node',
            namespace=join(namespace),
            output='screen'
        ),
    )

    # Load composable component
    if components:
        actions.append(
            LoadComposableNodes(
                target_container=(namespace, '/', 'component_container_node'),
                composable_node_descriptions=components
            ),
        )

    return actions