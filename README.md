# LIMO Training

ROS 2 Humble development workspace for the AgileX LIMO robot. The repository contains the robot description, Gazebo Sim bringup, `ros2_control` configuration, hardware bringup, an experimental hardware interface, EKF odometry, and SLAM Toolbox mapping/localization.

> This repository is under active development and is intended for development and training. Review the configuration and safety behavior before using it on real hardware.

## Supported environment

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Sim through `ros_gz`
- Repository branch: `humble`

## Packages

| Package | Purpose |
| --- | --- |
| [`limo_description`](limo_description/) | LIMO URDF/Xacro model, meshes, sensors, `ros2_control` integration points, and RViz configuration. |
| [`limo_simulation`](limo_simulation/) | Gazebo Sim bringup, sensor bridges, `gz_ros2_control`, joystick teleoperation, IMU filtering, safety components, and velocity multiplexing. |
| [`limo_hardware`](limo_hardware/) | Real-hardware `ros2_control` bringup and differential-drive controller configuration. |
| [`limo_interface`](limo_interface/) | Experimental custom `hardware_interface::SystemInterface` using per-joint ROS topics. It is not enabled by default. |
| [`limo_navigation`](limo_navigation/) | Robot Localization EKF plus SLAM Toolbox mapping and localization bringup. This is not a complete Nav2 navigation stack. |

## External dependencies

The repository expects the normal ROS 2 dependencies declared in each `package.xml`. It also uses packages that may be maintained in separate repositories:

- `safety_imu`
- `safety_hardware`
- `joint_state_topic_hardware_interface`
- `gz_ros2_control`
- `slam_toolbox`
- `robot_localization`

Place all required source packages in the same workspace before building.

## Build

```bash
mkdir -p ~/colcon_ws/src
cd ~/colcon_ws/src
git clone -b humble git@github.com:uzir91/limo-training.git

cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Add the workspace setup to a new terminal before running a launch file:

```bash
source /opt/ros/humble/setup.bash
source ~/colcon_ws/install/setup.bash
```

## Quick start

### Display the robot model

```bash
ros2 launch limo_description description.launch.py namespace:=limo
```

### Start the simulation

```bash
ros2 launch limo_simulation simulation.launch.py namespace:=limo
```

Run Gazebo without its graphical client:

```bash
ros2 launch limo_simulation simulation.launch.py namespace:=limo gui:=false rviz:=false
```

For NVIDIA PRIME render offload:

```bash
ros2 launch limo_simulation simulation.launch.py namespace:=limo gpu:=nvidia
```

### Start SLAM mapping in simulation

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  simulation:=true \
  mapping:=true
```

### Start localization from a serialized SLAM Toolbox map

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  simulation:=true \
  mapping:=false \
  map_filename:=/absolute/path/to/map
```

`map_filename` is the serialized SLAM Toolbox map name/path, not only a Nav2 `.yaml` occupancy-grid file.

### Start the hardware controller manager

Start the hardware driver that provides the configured joint-state transport, then run:

```bash
ros2 launch limo_hardware hardware.launch.py namespace:=limo
```

## Velocity command path

The simulation configuration uses `twist_mux` before the differential-drive controller. Common command inputs include:

- `/limo/nav/cmd_vel`
- `/limo/joy/cmd_vel`
- `/limo/key/cmd_vel`
- `/limo/rqt/cmd_vel`
- `/limo/ext/cmd_vel`

Example external command:

```bash
ros2 topic pub --rate 10 /limo/ext/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

Stop the publisher with `Ctrl+C`.

## Namespaced configuration

Simulation and navigation first look for configuration under:

```text
config/<namespace>/
```

For example, namespace `limo` uses `config/limo/`. If a namespaced file is missing, the launch code falls back to the package-level default configuration.

## Current limitations

- `limo_navigation` currently starts the simulation bringup and uses simulation time internally. Real-hardware navigation integration still needs cleanup.
- `limo_navigation` provides EKF and SLAM Toolbox bringup, but does not launch the complete Nav2 planner/controller stack.
- `limo_interface` is experimental and is currently commented out in the hardware `ros2_control` Xacro.
- Hardware and safety parameters must be validated on the real robot before operation.

## License

Apache License 2.0. See [LICENSE](LICENSE).
