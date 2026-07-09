from os.path import join
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.conditions import IfCondition , UnlessCondition
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_context(context, *args, **kwargs):
    # Resolve all argument values
    simulation = context.launch_configurations.get('simulation', 'false').lower() in ['true', '1', 'yes']
    joint_state_enable = context.launch_configurations.get('joint_state_enable', 'false').lower() in ['true', '1', 'yes']
    joint_state_gui_enable = context.launch_configurations.get('joint_state_gui_enable', 'true').lower() in ['true', '1', 'yes']
    rviz = context.launch_configurations.get('rviz', 'true').lower() in ['true', '1', 'yes']
    rviz_config = context.launch_configurations.get('rviz_config', 'description.rviz')

    pkg_limo_description = get_package_share_directory('limo_description')
    xacro_path = join(pkg_limo_description, 'urdf', 'assembly.urdf.xacro')
    rviz_path = join(pkg_limo_description, 'rviz', rviz_config)

    actions = []

    actions.append(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': Command([
                    PathJoinSubstitution([FindExecutable(name='xacro')]), ' ',
                    xacro_path,
                    ' simulation:=', str(simulation).lower()
                ]),
                'use_sim_time': simulation
            }]
        )
    )

    # Joint State Publisher logic
    if joint_state_gui_enable:
        actions.append(
            Node(
                name='joint_state_publisher_gui_node',
                package='joint_state_publisher_gui',
                executable='joint_state_publisher_gui',
                output='screen',
                parameters=[{'use_sim_time': simulation}]
            )
        )
    elif joint_state_enable:
        actions.append(
            Node(
                name='joint_state_publisher_node',
                package='joint_state_publisher',
                executable='joint_state_publisher',
                output='screen',
                parameters=[{'use_sim_time': simulation}]
            )
        )

    # RViz logic
    if rviz:
        actions.append(
            Node(
                name='rviz2_node',
                package='rviz2',
                executable='rviz2',
                output='screen',
                parameters=[{'use_sim_time': simulation}],
                arguments=['-d', rviz_path]
            )
        )

    return actions

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("simulation", default_value="false", description="true for simulation"),
        DeclareLaunchArgument("joint_state_enable", default_value="false", description="enable joint state publisher"),
        DeclareLaunchArgument("joint_state_gui_enable", default_value="true", description="enable joint state publisher gui"),
        DeclareLaunchArgument("rviz", default_value="true", description="enable rviz"),
        DeclareLaunchArgument("rviz_config", default_value="description.rviz", description="rviz filename"),
        OpaqueFunction(function=generate_context)
    ])




# def generate_context(context, *args, **kwargs):

# def generate_launch_description():
#     return LaunchDescription([
#         DeclareLaunchArgument("simulation", default_value="false", description="true for simulation"),
#         DeclareLaunchArgument("joint_state_enable", default_value="false", description="enable joint state publisher"),
#         DeclareLaunchArgument("joint_state_gui_enable", default_value="true", description="enable joint state publisher gui"),
#         DeclareLaunchArgument("rviz", default_value="true", description="enable rviz"),
#         DeclareLaunchArgument("rviz_config", default_value="description.rviz", description="rviz filename"),

#         OpaqueFunction(function = generate_context),
        
#         Node(
#             package = 'robot_state_publisher',
#             executable = 'robot_state_publisher',
#             output = 'screen',
#             parameters = [{
#                 'robot_description': Command([
#                     PathJoinSubstitution([FindExecutable(name='xacro')]), ' ',
#                     PathJoinSubstitution([FindPackageShare('limo_description'), 'urdf', 'assembly.urdf.xacro']),
#                     ' ', 'simulation:=', LaunchConfiguration('simulation')
#                 ]),
#                 'use_sim_time': LaunchConfiguration('simulation')
#             }]
#         ),

#         GroupAction(
#             condition = IfCondition(LaunchConfiguration('joint_state_gui_enable')),
#             actions = [
#                 Node(
#                     name ='joint_state_publisher_gui_node',
#                     package ='joint_state_publisher_gui',
#                     executable ='joint_state_publisher_gui',
#                     output ='screen',
#                     parameters = [{
#                         'use_sim_time': LaunchConfiguration('simulation')
#                     }]
#                 )
#             ]
#         ),

#         GroupAction(
#             condition = UnlessCondition(LaunchConfiguration('joint_state_gui_enable')),
#             actions = [
#                 GroupAction(
#                     condition = IfCondition(LaunchConfiguration('joint_state_enable')),
#                     actions = [
#                         Node(
#                             name ='joint_state_publisher_node',
#                             package ='joint_state_publisher',
#                             executable ='joint_state_publisher',
#                             output ='screen',
#                             parameters = [{
#                                 'use_sim_time': LaunchConfiguration('simulation')
#                             }]
#                         )
#                     ]
#                 )
#             ]
#         ),

#         GroupAction(
#             condition = IfCondition(LaunchConfiguration('rviz')),
#             actions = [
#                 Node(
#                     name ='rviz2_node',
#                     package ='rviz2',
#                     executable ='rviz2',
#                     output ='screen',
#                     parameters = [{
#                         'use_sim_time': LaunchConfiguration('simulation')
#                     }],
#                     arguments=[
#                         '-d',
#                         PathJoinSubstitution([
#                             FindPackageShare('limo_description'),
#                             'rviz',
#                             LaunchConfiguration('rviz_config')
#                         ])
#                     ]
#                 )
#             ]
#         )
#     ])