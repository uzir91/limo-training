from os.path import join, exists, expanduser
from pathlib import Path
from os import popen, environ
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction, TimerAction, SetEnvironmentVariable
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import LifecycleNode, Node, PushRosNamespace, ComposableNodeContainer, LoadComposableNodes
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.descriptions import ParameterFile, ComposableNode

from nav2_common.launch import RewrittenYaml

def replace_extension(path: str, extension: str) -> str:
    path = path.strip()
    extension = extension.strip()

    if not path:
        return ""

    file_path = Path(path).expanduser()

    if extension == "":
        return str(file_path.with_suffix(""))

    if not extension.startswith("."):
        extension = f".{extension}"

    return str(file_path.with_suffix(extension))

def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=generate_context)
    ])

def generate_context(context, *args, **kwargs):
    # --- Resolve arguments ---
    GetArgument = context.launch_configurations.get
    FindPackage = get_package_share_directory
    home_dir = expanduser('~')

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
    map_filename = expanduser(GetArgument('map_filename', ''))
    ekf_odom_filename = GetArgument('ekf_odom_filename', 'ekf_odom.yaml')
    slam_filename = GetArgument('slam_filename', 'slam.yaml')
    localization_filename = GetArgument('localization_filename', 'localization.yaml')
    controller_server_filename = GetArgument('controller_server_filename', 'controller_server.yaml')
    default_nav_through_poses_bt_xml_filename = GetArgument('default_nav_through_poses_bt_xml_filename', 'navigate_through_poses_w_replanning_and_recovery.xml')
    default_nav_to_pose_bt_xml_filename = GetArgument('default_nav_to_pose_bt_xml_filename', 'navigate_to_pose_w_replanning_and_recovery.xml')
    rviz_filename = GetArgument('rviz_filename', 'simulation.rviz')

    ekf_odom_path = GetArgument('ekf_odom_path', join(limo_navigation_pkg, 'config', namespace, ekf_odom_filename))
    slam_path = GetArgument('slam_path', join(limo_navigation_pkg, 'config', namespace, slam_filename))
    localization_path = GetArgument('localization_path', join(limo_navigation_pkg, 'config', namespace, localization_filename))
    controller_server_path = GetArgument('controller_server_path', join(limo_navigation_pkg, 'config', namespace, controller_server_filename))
    default_nav_through_poses_bt_xml_path = GetArgument('default_nav_through_poses_bt_xml_path', join(limo_navigation_pkg, 'config', namespace, default_nav_through_poses_bt_xml_filename))
    default_nav_to_pose_bt_xml_path = GetArgument('default_nav_to_pose_bt_xml_path', join(limo_navigation_pkg, 'config', namespace, default_nav_to_pose_bt_xml_filename))
    rviz_path = GetArgument('rviz_path', join(limo_navigation_pkg, 'rviz', rviz_filename))

    if not exists(ekf_odom_path):
        ekf_odom_path = join(limo_navigation_pkg, 'config', 'ekf_odom.yaml')
    if not exists(slam_path):
        slam_path = join(limo_navigation_pkg, 'config', 'slam.yaml')
    if not exists(localization_path):
        localization_path = join(limo_navigation_pkg, 'config', 'localization.yaml')
    if not exists(controller_server_path):
        controller_server_path = join(limo_navigation_pkg, 'config', 'controller_server.yaml')
    if not exists(default_nav_through_poses_bt_xml_path):
        default_nav_through_poses_bt_xml_path = join(limo_navigation_pkg, 'config', 'navigate_through_poses_w_replanning_and_recovery.xml')
    if not exists(default_nav_to_pose_bt_xml_path):
        default_nav_to_pose_bt_xml_path = join(limo_navigation_pkg, 'config', 'navigate_to_pose_w_replanning_and_recovery.xml')
    if not exists(rviz_path):
        rviz_path = join(limo_navigation_pkg, 'rviz', 'navigation.rviz')

    gpu_environment = []
    actions = []
    components = []
    lifecycles_localization = []
    lifecycles_navigation = []
    lifecycles_isolated = []

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

    if bool(simulation):
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
                            'gui': f'{gui}',
                            'rviz': f'False',
                        }.items(),
                    )
                ],
            )
        )
    else:
        # Limo hardware
        actions.append(
            GroupAction(
                scoped=True,
                forwarding=False,
                actions=[
                    *gpu_environment,
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            limo_hardware_launch
                        ),
                        launch_arguments={
                            'namespace': f'{join(namespace)}',
                            'gpu': f'{gpu}',
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
                {'use_sim_time': simulation},
            ],
            remappings=[
                ('odometry/filtered', 'odom_ekf/filtered'),
            ],
        ),
    )

    # SLAM node
    # slam_node = 'slam_node'
    if mapping:
        actions.append(
            Node(
                package='slam_toolbox',
                executable='sync_slam_toolbox_node',
                namespace=join(namespace),
                name='slam_toolbox',
                output='screen',
                parameters=[
                    # ParameterFile(
                    #     RewrittenYaml(
                    #         source_file=slam_path,
                    #         root_key=None,
                    #         param_rewrites={
                    #             'odom_frame': join(namespace, 'odom'),
                    #             'base_frame': join(namespace, 'base_footprint'),
                    #         },
                    #         convert_types=True,
                    #     ),
                    #     allow_substs=True,
                    # ),
                    slam_path,
                    {'odom_frame': join(namespace, 'odom')},
                    {'base_frame': join(namespace, 'base_footprint')},
                    {'map_file_name': replace_extension(map_filename, '')},
                    {'map_start_pose': [0.0, 0.0, 0.0]},
                    {'use_sim_time': simulation},
                ],
                remappings=[
                ],
            ),
        )
        lifecycles_localization.append('slam_toolbox');
    else:
        # Localization node
        actions.append(
            Node(
                package='slam_toolbox',
                executable='localization_slam_toolbox_node',
                namespace=join(namespace),
                name='slam_toolbox',
                output='screen',
                parameters=[
                    # ParameterFile(
                    #     RewrittenYaml(
                    #         source_file=localization_path,
                    #         root_key=None,
                    #         param_rewrites={
                    #             'odom_frame': join(namespace, 'odom'),
                    #             'base_frame': join(namespace, 'base_footprint'),
                    #         },
                    #         convert_types=True,
                    #     ),
                    #     allow_substs=True,
                    # ),
                    localization_path,
                    {'odom_frame': join(namespace, 'odom')},
                    {'base_frame': join(namespace, 'base_footprint')},
                    {'map_file_name': replace_extension(map_filename, '')},
                    {'map_start_pose': [0.0, 0.0, 0.0]},
                    {'use_sim_time': simulation},
                ],
                remappings=[
                ],
            ),
        )
        lifecycles_localization.append('slam_toolbox');

    # # Composoble Container
    # actions.append(
    #     Node(
    #         package='rclcpp_components',
    #         executable='component_container_isolated',
    #         name='component_container_node',
    #         namespace=join(namespace),
    #         output='screen'
    #     ),
    # )

    actions.append(
        Node(
            package='nav2_bt_navigator',
            # plugin='nav2_bt_navigator::BtNavigator',
            executable='bt_navigator',
            namespace=join(namespace),
            name='bt_navigator',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'bt_navigator_navigate_through_poses_rclcpp_node.ros__parameters.use_sim_time': f"{simulation}",
                            'bt_navigator_navigate_to_pose_rclcpp_node.ros__parameters.use_sim_time': f"{simulation}",
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
                {'global_frame': 'map'},
                {'robot_base_frame': join(namespace, 'base_footprint')},
                {'default_nav_through_poses_bt_xml': default_nav_through_poses_bt_xml_path},
                {'default_nav_to_pose_bt_xml': default_nav_to_pose_bt_xml_path},
            ],
            remappings=[
                ('odom', 'odom_ekf/filtered'),
            ],
        ),
    )
    lifecycles_navigation.append('bt_navigator');

    static_map_topic = 'map' if bool(mapping) else 'contour_map'
    speed_map_filename = replace_extension(map_filename, 'speed2.yaml')
    planner_plugin = f'["speed"]' if not mapping and Path(speed_map_filename).exists() else "[]"
    contour_map_filename = replace_extension(map_filename, 'yaml')
    actions.append(
        Node(
            package='nav2_planner',
            # plugin='nav2_planner::PlannerServer',
            executable='planner_server',
            namespace=join(namespace),
            name='planner_server',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'global_costmap.global_costmap.ros__parameters.use_sim_time': f"{simulation}",
                            'global_costmap.global_costmap.ros__parameters.global_frame': 'map',
                            'global_costmap.global_costmap.ros__parameters.robot_base_frame': join(namespace, 'base_footprint'),
                            'global_costmap.global_costmap.ros__parameters.obstacle_layer.scan.topic': join('/', namespace, 'scan/data'),
                            'global_costmap.global_costmap.ros__parameters.static_layer.map_topic': join('/', namespace, static_map_topic),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
            ],
            remappings=[
            ],
        ),
    )
    lifecycles_navigation.append('planner_server');

    actions.append(
        Node(
            package='nav2_controller',
            # plugin='nav2_controller::ControllerServer',
            executable='controller_server',
            namespace=join(namespace),
            name='controller_server',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'local_costmap.local_costmap.ros__parameters.use_sim_time': f"{simulation}",
                            'local_costmap.local_costmap.ros__parameters.global_frame': join(namespace, 'odom'),
                            'local_costmap.local_costmap.ros__parameters.robot_base_frame': join(namespace, 'base_footprint'),
                            'local_costmap.local_costmap.ros__parameters.planner_plugins': planner_plugin,
                            'local_costmap.local_costmap.ros__parameters.voxel_layer.scan.topic': join('/', namespace, 'scan/data'),
                            'local_costmap.local_costmap.ros__parameters.static_layer.map_topic': join('/', namespace, static_map_topic),
                            'local_costmap.local_costmap.ros__parameters.speed_filter.filter_info_topic': join('/', namespace, 'speed_costmap_filter_info'),
                            'local_costmap.local_costmap.ros__parameters.speed_filter.speed_limit_topic': join('/', namespace, 'speed_limit'),
                            'local_costmap.local_costmap.ros__parameters.speed_filter.enabled': str(Path(speed_map_filename).exists() and bool(speed_map_filename)).lower(),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
            ],
            remappings=[
                ('cmd_vel', 'nav/cmd_vel'),
                ('odom', 'odom_ekf/filtered'),
            ],
        )
    )
    lifecycles_navigation.append('controller_server');

    if not mapping:
        if Path(speed_map_filename).exists() and bool(speed_map_filename):
            actions.append(
                Node(
                    package='nav2_map_server',
                    executable='costmap_filter_info_server',
                    namespace=join(namespace),
                    name='speed_costmap_filter_info_server',
                    parameters=[
                        ParameterFile(
                            RewrittenYaml(
                                source_file=controller_server_path,
                                root_key=join(namespace),
                                param_rewrites={
                                },
                                convert_types=True,
                            ),
                            allow_substs=True,
                        ),
                        {'use_sim_time': simulation},
                        {'mask_topic': join('/', namespace, 'speed_filter_mask')},
                    ],
                    remappings=[
                    ],
                ),
            )
            lifecycles_navigation.append('speed_costmap_filter_info_server');

            actions.append(
                Node(
                    package='nav2_map_server',
                    executable='map_server',
                    namespace=join(namespace),
                    name='speed_filter_mask_server',
                    parameters=[
                        ParameterFile(
                            RewrittenYaml(
                                source_file=controller_server_path,
                                root_key=join(namespace),
                                param_rewrites={
                                },
                                convert_types=True,
                            ),
                            allow_substs=True,
                        ),
                        {'use_sim_time': simulation},
                        {'yaml_filename': speed_map_filename},
                    ],
                    remappings=[
                    ],
                ),
            )
            lifecycles_navigation.append('speed_filter_mask_server');

        if Path(contour_map_filename).exists() and bool(contour_map_filename):
            actions.append(
                Node(
                    package='nav2_map_server',
                    executable='map_server',
                    namespace=join(namespace),
                    name='contour_map_server',
                    parameters=[
                        ParameterFile(
                            RewrittenYaml(
                                source_file=controller_server_path,
                                root_key=join(namespace),
                                param_rewrites={
                                },
                                convert_types=True,
                            ),
                            allow_substs=True,
                        ),
                        {'use_sim_time': simulation},
                        {'yaml_filename': contour_map_filename},
                    ],
                    remappings=[
                    ],
                ),
            )
            lifecycles_navigation.append('contour_map_server');

    actions.append(
        Node(
            package='nav2_behaviors',
            # plugin='behavior_server::BehaviorServer',
            executable='behavior_server',
            namespace=join(namespace),
            name='behavior_server',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'behavior_server.ros__parameters.use_sim_time': f"{simulation}",
                            'behavior_server.ros__parameters.global_frame': join(namespace, 'odom'),
                            'behavior_server.ros__parameters.robot_base_frame': join(namespace, 'base_footprint'),
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
            ],
            remappings=[
                ('cmd_vel', 'nav/cmd_vel'),
            ],
        ),
    )
    lifecycles_navigation.append('behavior_server');

    actions.append(
        Node(
            package='nav2_smoother',
            # plugin='nav2_smoother::SmootherServer',
            executable='smoother_server',
            namespace=join(namespace),
            name='smoother_server',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'smoother_server.ros__parameters.use_sim_time': f"{simulation}",
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
            ],
            remappings=[
            ],
        ),
    )
    lifecycles_navigation.append('smoother_server');

    actions.append(
        Node(
            package='nav2_waypoint_follower',
            # plugin='nav2_waypoint_follower::WaypointFollower',
            executable='waypoint_follower',
            namespace=join(namespace),
            name='waypoint_follower',
            parameters=[
                ParameterFile(
                    RewrittenYaml(
                        source_file=controller_server_path,
                        root_key=join(namespace),
                        param_rewrites={
                            'waypoint_follower.ros__parameters.use_sim_time': f"{simulation}",
                        },
                        convert_types=True,
                    ),
                    allow_substs=True,
                ),
                {'use_sim_time': simulation},
            ],
            remappings=[
            ],
        ),
    )
    lifecycles_navigation.append('waypoint_follower');

    # SLAM Lifecycle Manager
    if lifecycles_localization:
        actions.append(
            Node(
                package='nav2_lifecycle_manager',
                # plugin='nav2_lifecycle_manager::LifecycleManager',
                executable='lifecycle_manager',
                namespace=join(namespace),
                name='lifecycle_manager_localization',
                parameters=[
                    {
                        'use_sim_time': simulation,
                        'autostart': True,
                        'node_names': lifecycles_localization,
                        'bond_timeout': 0.0,
                    },
                ],
            ),
        )

    # Nav2 Lifecycle Manager
    if lifecycles_navigation:
        actions.append(
            Node(
                package='nav2_lifecycle_manager',
                # plugin='nav2_lifecycle_manager::LifecycleManager',
                executable='lifecycle_manager',
                namespace=join(namespace),
                name='lifecycle_manager_navigation',
                parameters=[
                    {
                        'use_sim_time': simulation,
                        'autostart': True,
                        'node_names': lifecycles_navigation,
                        'bond_timeout': 0.0,
                    },
                ],
            ),
        )

    # Isolated Lifecycle Manager
    if lifecycles_isolated:
        actions.append(
            Node(
                package='nav2_lifecycle_manager',
                # plugin='nav2_lifecycle_manager::LifecycleManager',
                executable='lifecycle_manager',
                namespace=join(namespace),
                name='lifecycle_manager_isolated',
                parameters=[
                    {
                        'use_sim_time': simulation,
                        'autostart': True,
                        'node_names': lifecycles_isolated,
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
                        name='rviz2',
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
                        ],
                    )
                ],
            )
        )

    # # Load composable component
    if components:
        actions.append(
            LoadComposableNodes(
                target_container=(namespace, '/', 'component_container_node'),
                composable_node_descriptions=components,
            )
        )

    return actions