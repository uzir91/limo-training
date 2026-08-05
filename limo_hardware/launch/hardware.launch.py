from os.path import join, exists
from os import popen, environ
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, TimerAction, SetEnvironmentVariable, ExecuteProcess
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node, PushRosNamespace, ComposableNodeContainer, LoadComposableNodes
from launch_ros.substitutions import FindPackageShare, ExecutableInPackage
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
    camera_throttle_filename = GetArgument('camera_throttle_filename', 'camera_throttle.yaml')
    camera_info_throttle_filename = GetArgument('camera_info_throttle_filename', 'camera_info_throttle.yaml')
    apriltag_filename = GetArgument('apriltag_filename', 'apriltag.yaml')
    apriltag_pose_filename = GetArgument('apriltag_pose_filename', 'apriltag_pose.yaml')
    audio_capture_filename = GetArgument('audio_capture_filename', 'audio_capture.yaml')
    sr_vosk_filename = GetArgument('sr_vosk_filename', 'sr_vosk.yaml')
    tts_piper_filename = GetArgument('tts_piper_filename', 'tts_piper.yaml')
    audio_play_filename = GetArgument('audio_play_filename', 'audio_play.yaml')
    ocr_tesseract_filename = GetArgument('ocr_tesseract_filename', 'ocr_tesseract.yaml')
    ocr_rapid_filename = GetArgument('ocr_rapid_filename', 'ocr_rapid.yaml')
    traffic_light_filename = GetArgument('traffic_light_filename', 'traffic_light.yaml')
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
    camera_throttle_path = GetArgument('camera_throttle_path', join(limo_hardware_pkg, 'config', namespace, camera_throttle_filename))
    camera_info_throttle_path = GetArgument('camera_info_throttle_path', join(limo_hardware_pkg, 'config', namespace, camera_info_throttle_filename))
    apriltag_path = GetArgument('apriltag_path', join(limo_hardware_pkg, 'config', namespace, apriltag_filename))
    apriltag_pose_path = GetArgument('apriltag_pose_path', join(limo_hardware_pkg, 'config', namespace, apriltag_pose_filename))
    audio_capture_path = GetArgument('audio_capture_path', join(limo_hardware_pkg, 'config', namespace, audio_capture_filename))
    sr_vosk_path = GetArgument('sr_vosk_path', join(limo_hardware_pkg, 'config', namespace, sr_vosk_filename))
    tts_piper_path = GetArgument('tts_piper_path', join(limo_hardware_pkg, 'config', namespace, tts_piper_filename))
    audio_play_path = GetArgument('audio_play_path', join(limo_hardware_pkg, 'config', namespace, audio_play_filename))
    ocr_tesseract_path = GetArgument('ocr_tesseract_path', join(limo_hardware_pkg, 'config', namespace, ocr_tesseract_filename))
    ocr_rapid_path = GetArgument('ocr_rapid_path', join(limo_hardware_pkg, 'config', namespace, ocr_rapid_filename))
    traffic_light_path = GetArgument('traffic_light_path', join(limo_hardware_pkg, 'config', namespace, traffic_light_filename))
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
    if not exists(camera_throttle_path):
        camera_throttle_path = join(limo_hardware_pkg, 'config', 'camera_throttle.yaml')
    if not exists(camera_info_throttle_path):
        camera_info_throttle_path = join(limo_hardware_pkg, 'config', 'camera_info_throttle.yaml')
    if not exists(apriltag_path):
        apriltag_path = join(limo_hardware_pkg, 'config', 'apriltag.yaml')
    if not exists(apriltag_pose_path):
        apriltag_pose_path = join(limo_hardware_pkg, 'config', 'apriltag_pose.yaml')
    if not exists(audio_capture_path):
        audio_capture_path = join(limo_hardware_pkg, 'config', 'audio_capture.yaml')
    if not exists(sr_vosk_path):
        sr_vosk_path = join(limo_hardware_pkg, 'config', 'sr_vosk.yaml')
    if not exists(tts_piper_path):
        tts_piper_path = join(limo_hardware_pkg, 'config', 'tts_piper.yaml')
    if not exists(audio_play_path):
        audio_play_path = join(limo_hardware_pkg, 'config', 'audio_play.yaml')
    if not exists(ocr_tesseract_path):
        ocr_tesseract_path = join(limo_hardware_pkg, 'config', 'ocr_tesseract.yaml')
    if not exists(ocr_rapid_path):
        ocr_rapid_path = join(limo_hardware_pkg, 'config', 'ocr_rapid.yaml')
    if not exists(traffic_light_path):
        traffic_light_path = join(limo_hardware_pkg, 'config', 'traffic_light.yaml')
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
                ('/camera/depth_to_ir', 'camera/depth_to_ir'),
                ('/camera/depth_to_color', 'camera/depth_to_color'),
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

    # # Camera throttle
    # components.append(
    #     ComposableNode(
    #         package='image_throttle',
    #         plugin='image_throttle::ImageThrottleComponent',
    #         namespace=join(namespace),
    #         name='camera_throttle_node',
    #         parameters=[
    #             camera_throttle_path,
    #             {'use_sim_time': False},
    #         ],
    #         remappings=[
    #         ],
    #         # extra_arguments=[
    #         #     {
    #         #         'use_intra_process_comms': False,
    #         #     },
    #         # ],
    #     ),
    # )

    # Apriltag detection
    components.append(
        ComposableNode(
            package='apriltag_ros',
            plugin='AprilTagNode',
            namespace=join(namespace),
            name='apriltag_node',
            parameters=[
                apriltag_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('image_rect', 'camera/color/image_raw'),
                ('detections', 'apriltag/detections'),
            ],
            extra_arguments=[
                {
                    'use_intra_process_comms': True,
                },
            ],
        ),
    )

    # Apriltag pose
    components.append(
        ComposableNode(
            package='apriltag_pose',
            plugin='apriltag_pose::AprilTagPoseComponent',
            namespace=join(namespace),
            name='apriltag_pose_node',
            parameters=[
                apriltag_pose_path,
                {'use_sim_time': False},
            ],
            remappings=[
            ],
            extra_arguments=[
                {
                    'use_intra_process_comms': True,
                },
            ],
        ),
    )

    # Audio capture
    components.append(
        ComposableNode(
            package='audio_capture',
            plugin='audio_capture::AudioCaptureNode',
            namespace=join(namespace),
            name='audio_capture_node',
            parameters=[
                audio_capture_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('audio_stamped', 'capture/audio_stamped'),
                ('audio_info', 'capture/audio_info'),
                ('audio', 'capture/audio'),
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        ),
    )

    # Audio recognize
    components.append(
        ComposableNode(
            package='sr_vosk',
            plugin='sr_vosk::SrVoskComponent',
            namespace=join(namespace),
            name='sr_vosk_node',
            parameters=[
                sr_vosk_path,
                {'use_sim_time': False},
            ],
            remappings=[
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        ),
    )

    components.append(
        ComposableNode(
            package='tts_piper',
            plugin='tts_piper::TtsPiperComponent',
            namespace=join(namespace),
            name='tts_piper',
            parameters=[
                tts_piper_path,
                {'use_sim_time': False},
            ],
            remappings=[
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        )
    )

    components.append(
        ComposableNode(
            package='audio_play',
            plugin='audio_play::AudioPlayNode',
            namespace=join(namespace),
            name='audio_play',
            parameters=[
                audio_play_path,
                {'use_sim_time': False},
            ],
            remappings=[
                ('audio', 'tts/audio'),
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        )
    )

    # components.append(
    #     ComposableNode(
    #         package='ocr_tesseract',
    #         plugin='ocr_tesseract::OcrTesseractComponent',
    #         namespace=join(namespace),
    #         name='ocr_tesseract',
    #         parameters=[
    #             ocr_tesseract_path,
    #             {'use_sim_time': False},
    #         ],
    #         remappings=[
    #         ],
    #         # extra_arguments=[
    #         #     {
    #         #         'use_intra_process_comms': True,
    #         #     },
    #         # ],
    #     )
    # )

    components.append(
        ComposableNode(
            package='ocr_rapid',
            plugin='ocr_rapid::OcrRapidComponent',
            namespace=join(namespace),
            name='ocr_rapid',
            parameters=[
                ocr_rapid_path,
                {'use_sim_time': True},
            ],
            remappings=[
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        )
    )

    components.append(
        ComposableNode(
            package='traffic_light',
            plugin='traffic_light::TrafficLightComponent',
            namespace=join(namespace),
            name='traffic_light',
            parameters=[
                traffic_light_path,
                {'use_sim_time': False},
            ],
            remappings=[
            ],
            # extra_arguments=[
            #     {
            #         'use_intra_process_comms': True,
            #     },
            # ],
        )
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

    # start node-red
    actions.append(
        ExecuteProcess(
            cmd=[
                ExecutableInPackage(
                    package='limo_hardware',
                    executable='start_node_red.sh',
                ),
            ],
            output='screen',
        )
    )

    return actions