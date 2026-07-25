from os.path import join, exists
from os import popen, environ
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, TimerAction, SetEnvironmentVariable
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import LifecycleNode, Node, PushRosNamespace, ComposableNodeContainer
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.descriptions import ParameterFile, ComposableNode

from nav2_common.launch import RewrittenYaml

def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=generate_context)
    ])

def generate_context(context, *args, **kwargs):
    # --- Resolve arguments ---
    GetArgument = context.launch_configurations.get
    FindPackage = get_package_share_directory

    limo_navigation_pkg = FindPackage('limo_navigation')
    limo_simulation_pkg = FindPackage('limo_simulation')
    limo_hardware_pkg = FindPackage('limo_hardware')

    limo_simulation_launch = join(limo_simulation_pkg, 'launch', 'simulation.launch.py')
    limo_hardware_launch = join(limo_hardware_pkg, 'launch', 'hardware.launch.py')

    namespace = GetArgument('namespace', 'limo')
    simulation = GetArgument('simulation', 'true').lower() in ['true', '1', 'yes']
    gpu = GetArgument('gpu', 'default').lower()
    rviz = GetArgument('rviz', 'true').lower() in ['true', '1', 'yes']
    gui = GetArgument('gui', 'true').lower() in ['true', '1', 'yes']
    mapping = GetArgument('mapping', 'true').lower() in ['true', '1', 'yes']
    map_filename = GetArgument('map_filename', '')
    ekf_odom_filename = GetArgument('ekf_odom_filename', 'ekf_odom.yaml')
    slam_filename = GetArgument('slam_filename', 'slam.yaml')
    localization_filename = GetArgument('localization_filename', 'localization.yaml')
    rviz_filename = GetArgument('rviz_filename', 'simulation.rviz')

    ekf_odom_path = GetArgument('ekf_odom_path', join(limo_navigation_pkg, 'config', namespace, ekf_odom_filename))
    slam_path = GetArgument('slam_path', join(limo_navigation_pkg, 'config', namespace, slam_filename))
    localization_path = GetArgument('localization_path', join(limo_navigation_pkg, 'config', namespace, localization_filename))
    rviz_path = GetArgument('rviz_path', join(limo_navigation_pkg, 'rviz', rviz_filename))

    if not exists(ekf_odom_path):
        ekf_odom_path = join(limo_navigation_pkg, 'config', 'ekf_odom.yaml')
    if not exists(slam_path):
        slam_path = join(limo_navigation_pkg, 'config', 'slam.yaml')
    if not exists(localization_path):
        localization_path = join(limo_navigation_pkg, 'config', 'localization.yaml')
    if not exists(rviz_path):
        rviz_path = join(limo_navigation_pkg, 'rviz', 'navigation.rviz')

    gpu_environment = []
    actions = []
    components = []
    slam_lifecycles = []
    localization_lifecycles = []

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

    # Limo simulation
    actions.append(
        GroupAction(
            scoped=True,
            forwarding=False,
            actions=[
                *gpu_environment,
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        limo_simulation_launch
                    ),
                    launch_arguments={
                        'namespace': f'{join(namespace)}',
                        'gpu': f'{gpu}',
                        'simulation': f'{simulation}',
                        'gui': f'{gui}',
                        'rviz': f'False',
                    }.items(),
                )
            ],
        )
    )

    # EKF odom
    actions.append(
        Node(
            package='robot_localization',
            executable='ekf_node',
            namespace=join(namespace),
            name='ekf_odom_node',
            output='screen',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=ekf_odom_path,
                        root_key=None,
                        param_rewrites={
                            'odom_frame': join(namespace, 'odom'),
                            'base_link_frame': join(namespace, 'base_footprint'),
                            'world_frame': join(namespace, 'odom'),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': True},
            ],
            remappings=[
                ('odometry/filtered', 'odom_ekf/filtered'),
            ],
        ),
    )

    # SLAM node
    actions.append(
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            namespace=join(namespace),
            name='slam_node',
            output='screen',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=slam_path,
                        root_key=None,
                        param_rewrites={
                            'odom_frame': join(namespace, 'odom'),
                            'base_frame': join(namespace, 'base_footprint'),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'map_file_name': map_filename},
                {'map_start_pose': [0.0, 0.0, 0.0]},
                {'use_sim_time': True},
            ],
            remappings=[
                # ('/map', join(namespace, 'map')),
                # ('/map_metadata', join(namespace, 'map_metadata')),
            ],
        ),
    )
    slam_lifecycles.append('slam_node');

    # Localization node
    actions.append(
        Node(
            package='slam_toolbox',
            executable='localization_slam_toolbox_node',
            namespace=join(namespace),
            name='localization_node',
            output='screen',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=localization_path,
                        root_key=None,
                        param_rewrites={
                            'odom_frame': join(namespace, 'odom'),
                            'base_frame': join(namespace, 'base_footprint'),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'map_file_name': map_filename},
                {'map_start_pose': [0.0, 0.0, 0.0]},
                {'use_sim_time': True},
            ],
            remappings=[
                # ('/map', join(namespace, 'map')),
                # ('/map_metadata', join(namespace, 'map_metadata')),
            ],
        ),
    )
    localization_lifecycles.append('localization_node');

    # SLAM Lifecycle Manager
    components.append(
        ComposableNode(
            package='nav2_lifecycle_manager',
            plugin='nav2_lifecycle_manager::LifecycleManager',
            namespace=join(namespace),
            name='slam_lifecycle_manager_component',
            parameters=[
                {
                    'autostart': mapping,
                    'node_names': slam_lifecycles,
                    'bond_timeout': 0.0,
                },
            ],
        ),
    )

    # Localization Lifecycle Manager
    components.append(
        ComposableNode(
            package='nav2_lifecycle_manager',
            plugin='nav2_lifecycle_manager::LifecycleManager',
            namespace=join(namespace),
            name='localization_lifecycle_manager_component',
            parameters=[
                {
                    'autostart': not mapping,
                    'node_names': localization_lifecycles,
                    'bond_timeout': 0.0,
                },
            ],
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
                        namespace=join(namespace),
                        package='rviz2',
                        executable='rviz2',
                        output='screen',
                        parameters=[
                            {'use_sim_time': True},
                        ],
                        arguments=[
                            '-d',
                            rviz_path,
                        ],
                        remappings=[
                            ('/goal_pose', 'goal_pose'),
                            ('/clicked_point', 'clicked_point'),
                            ('/initialpose', 'initialpose'),
                            ('/slam_toolbox/serialize_map', 'slam_toolbox/serialize_map'),
                            ('/slam_toolbox/deserialize_map', 'slam_toolbox/deserialize_map'),
                            ('/slam_toolbox/save_map', 'slam_toolbox/save_map'),
                            ('/slam_toolbox/clear_changes', 'slam_toolbox/clear_changes'),
                            ('/slam_toolbox/manual_loop_closure', 'slam_toolbox/manual_loop_closure'),
                            ('/slam_toolbox/clear_queue', 'slam_toolbox/clear_queue'),
                            ('/slam_toolbox/toggle_interactive_mode', 'slam_toolbox/toggle_interactive_mode'),
                            ('/slam_toolbox/pause_new_measurements', 'slam_toolbox/pause_new_measurements'),
                            ('/slam_toolbox/add_submap', 'slam_toolbox/add_submap'),
                            ('/slam_toolbox/merge_submaps', 'slam_toolbox/merge_submaps'),
                        ],
                    )
                ],
            )
        )

    # Composoble Container
    if components:
        actions.append(
            ComposableNodeContainer(
                package='rclcpp_components',
                executable='component_container_mt',
                namespace=join(namespace),
                name='component_container_node',
                composable_node_descriptions=components,
                output='screen',
                emulate_tty=True,
            )
        )

    return actions