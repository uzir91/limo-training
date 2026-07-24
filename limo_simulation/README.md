# limo_simulation

ROS 2 Humble Gazebo Sim bringup for the AgileX LIMO robot.

The package starts the robot description, Gazebo Sim world, robot spawn, ROS/Gazebo sensor bridge, `gz_ros2_control`, differential-drive controllers, joystick input, IMU filtering, safety components, `twist_mux`, and optional RViz.

## Included runtime pipeline

```text
Gazebo sensors
  -> ros_gz_bridge
  -> IMU complementary filter
  -> safety_imu

Joystick / navigation / external velocity sources
  -> twist_mux
  -> diff_drive_controller
  -> gz_ros2_control
  -> Gazebo model
```

The launch file also loads `safety_hardware` in the shared multithreaded component container.

## Required packages

In addition to the package dependencies, ensure these packages are available in the workspace or underlay:

- `gz_ros2_control`
- `safety_imu`
- `safety_hardware`

## Build

```bash
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to limo_simulation
source install/setup.bash
```

## Launch

```bash
ros2 launch limo_simulation simulation.launch.py namespace:=limo
```

Headless Gazebo server without RViz:

```bash
ros2 launch limo_simulation simulation.launch.py \
  namespace:=limo \
  gui:=false \
  rviz:=false
```

NVIDIA PRIME render offload:

```bash
ros2 launch limo_simulation simulation.launch.py \
  namespace:=limo \
  gpu:=nvidia
```

Use the empty world:

```bash
ros2 launch limo_simulation simulation.launch.py \
  namespace:=limo \
  world_filename:=empty.sdf
```

## Common launch arguments

| Argument | Default | Description |
| --- | --- | --- |
| `namespace` | `limo` | Namespace and Gazebo entity name. |
| `gpu` | `default` | GPU environment selection. Use `nvidia` for NVIDIA PRIME offload. |
| `rviz` | `true` | Starts RViz. |
| `gui` | `true` | Starts the Gazebo graphical client. `false` runs server-only mode. |
| `world_filename` | `limo_world.sdf` | World file under `worlds/`. |
| `controller_manager_filename` | `controller_manager.yaml` | Namespaced controller configuration filename. |
| `ros2_control_filename` | `ros2_control.xacro` | Simulation hardware Xacro filename. |
| `joy_filename` | `joy.yaml` | Joystick driver configuration filename. |
| `teleop_twist_filename` | `teleop_twist.yaml` | Joystick-to-Twist configuration filename. |
| `imu_filter_filename` | `imu_filter.yaml` | Complementary-filter configuration filename. |
| `safety_imu_filename` | `safety_imu.yaml` | IMU safety configuration filename. |
| `safety_hardware_filename` | `safety_hardware.yaml` | Hardware safety configuration filename. |
| `twist_mux_filename` | `twist_mux.yaml` | Velocity arbitration and lock configuration filename. |
| `rviz_filename` | `simulation.rviz` | RViz configuration filename. |

Every file also has a corresponding `*_path` override for supplying an absolute or custom path.

## Namespaced configuration fallback

For namespace `limo`, the launch file first searches under:

```text
config/limo/
```

When a namespaced file is absent, it falls back to the default file directly under `config/`.

## Bridged sensor topics

For the default namespace:

```text
/limo/imu/data
/limo/scan/data
/limo/camera/image
/limo/camera/camera_info
/limo/camera/depth_image
/limo/camera/points
```

The simulation also bridges `/clock` and enables simulation time.

## Processed topics

```text
/limo/imu/filtering
/limo/imu/filtered
/limo/diff_drive_controller/odom
/limo/odom/filtered
/limo/safety_imu/error
/limo/hardware/error
```

## Velocity inputs

The default `twist_mux` configuration accepts:

```text
/limo/nav/cmd_vel
/limo/joy/cmd_vel
/limo/key/cmd_vel
/limo/rqt/cmd_vel
/limo/ext/cmd_vel
```

Example external command:

```bash
ros2 topic pub --rate 10 /limo/ext/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

## Useful checks

```bash
ros2 topic list | grep '^/limo'
ros2 control list_controllers -c /limo/controller_manager
ros2 topic echo /limo/scan/data
ros2 topic echo /limo/imu/filtered
ros2 topic echo /limo/diff_drive_controller/odom
```

## Safety note

The simulated safety pipeline is useful for integration testing, but simulation success does not prove that the same thresholds, timeouts, and failure behavior are safe on the physical robot.

## License

Apache License 2.0. See [LICENSE](LICENSE).
