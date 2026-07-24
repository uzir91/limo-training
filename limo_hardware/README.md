# limo_hardware

ROS 2 Humble bringup package for running the LIMO differential-drive controllers against a real-hardware joint-state transport.

The package combines `limo_description`, `ros2_control_node`, the joint-state broadcaster, the differential-drive controller, and an optional RViz session.

## Current hardware backend

The active backend in `urdf/ros2_control.xacro` is:

```text
joint_state_topic_hardware_interface/JointStateTopicSystem
```

It is configured with:

```text
node_namespace: /<namespace>
joint_commands_topic: /<namespace>/hardware/joint_states
joint_states_topic: /<namespace>/hardware/joint_states
```

For the default namespace, the configured transport topic is:

```text
/limo/hardware/joint_states
```

The robot driver or bridge responsible for this topic must be running before motion is expected.

The custom `limo_interface/LimoSystem` plugin is present in the repository, but its Xacro block is currently commented out and is not the default backend.

## Build

```bash
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to limo_hardware
source install/setup.bash
```

## Launch

```bash
ros2 launch limo_hardware hardware.launch.py namespace:=limo
```

Without RViz:

```bash
ros2 launch limo_hardware hardware.launch.py namespace:=limo rviz:=false
```

For NVIDIA PRIME render offload in RViz:

```bash
ros2 launch limo_hardware hardware.launch.py namespace:=limo gpu:=nvidia
```

## Launch arguments

| Argument | Default | Description |
| --- | --- | --- |
| `namespace` | `limo` | ROS namespace used by the robot and controller manager. |
| `gpu` | `default` | RViz GPU environment selection. Use `nvidia` for NVIDIA PRIME offload. |
| `rviz` | `true` | Starts RViz with `rviz/hardware.rviz`. |
| `controller_manager_path` | `config/controller_manager.yaml` | Controller-manager and differential-drive parameters. |
| `ros2_control_path` | `urdf/ros2_control.xacro` | Hardware-backend Xacro passed to `limo_description`. |

## Controllers

The launch file spawns:

- `joint_state_broadcaster`
- `diff_drive_controller`

Important differential-drive settings include:

- Wheel separation: `0.176 m`
- Wheel radius: `0.0482 m`
- Command timeout: `0.5 s`
- Linear velocity range: `-1.0` to `1.0 m/s`
- Angular velocity range: `-3.0` to `3.0 rad/s`
- Stamped velocity command enabled
- Odometry TF disabled; another localization source is expected to publish the required TF

## Useful checks

```bash
ros2 control list_controllers -c /limo/controller_manager
ros2 control list_hardware_interfaces -c /limo/controller_manager
ros2 topic echo /limo/joint_states
ros2 topic echo /limo/diff_drive_controller/odom
```

Check the exact controller command topic on the installed Humble controller:

```bash
ros2 topic list | grep diff_drive_controller
```

## Safety

Do not test the first command with the robot lifted only partly from the floor. Verify wheel direction, command timeout, emergency stop, and maximum velocity with all drive wheels safely clear or with the motors mechanically disconnected.

## License

Apache License 2.0. See [LICENSE](LICENSE).
