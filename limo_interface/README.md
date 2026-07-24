# limo_interface

Experimental ROS 2 Humble `hardware_interface::SystemInterface` plugin for bridging `ros2_control` wheel interfaces to per-joint ROS topics.

Plugin class:

```text
limo_interface/LimoSystem
```

C++ type:

```text
limo_interface::LimoSystem
```

## Status

This package is experimental. It builds and exports a hardware plugin, but it is not enabled by default in `limo_hardware/urdf/ros2_control.xacro`.

The current implementation actively wires only the velocity topic path. Position and effort structures are present, but their subscriptions and publishers are not enabled.

## Behavior

For every joint declared in the `ros2_control` hardware information, the plugin currently:

- Subscribes to `<joint_name>/state/velocity` using `std_msgs/msg/Float64`
- Publishes `<joint_name>/command/velocity` using `std_msgs/msg/Float64`
- Integrates received velocity into a wrapped joint position in the range `[-pi, pi]`
- Sets stale velocity feedback to zero after the configured timeout
- Exports position, velocity, and effort state and command interfaces to `ros2_control`

Unless the internal node is placed in another namespace by future code changes, these relative topic names resolve from the node's namespace.

## Build

```bash
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select limo_interface
source install/setup.bash
```

Confirm that the plugin is exported:

```bash
ros2 pkg prefix limo_interface
```

## Xacro usage

Use the plugin inside a `ros2_control` hardware block:

```xml
<ros2_control name="ros2_control_system" type="system">
  <hardware>
    <plugin>limo_interface/LimoSystem</plugin>

    <param name="wheel_front_left_joint_velocity_timeout">0.2</param>
    <param name="wheel_front_left_joint_velocity_state_dir">false</param>
    <param name="wheel_front_left_joint_velocity_command_dir">false</param>
  </hardware>

  <!-- Declare the required joints and interfaces here. -->
</ros2_control>
```

## Per-joint parameters

The plugin parses the following parameter pattern for every joint:

```text
<joint_name>_position_timeout
<joint_name>_velocity_timeout
<joint_name>_effort_timeout

<joint_name>_position_state_dir
<joint_name>_velocity_state_dir
<joint_name>_effort_state_dir

<joint_name>_position_command_dir
<joint_name>_velocity_command_dir
<joint_name>_effort_command_dir
```

Timeout defaults are `1.0 s`. Direction flags default to `false`.

In the current active implementation, velocity feedback timeout and velocity state direction are applied. Command direction is parsed but is not currently applied in `write()`.

## Example topics

For `wheel_front_left_joint`:

```text
wheel_front_left_joint/state/velocity
wheel_front_left_joint/command/velocity
```

Message type:

```text
std_msgs/msg/Float64
```

## Known limitations

- The internal executor thread is detached and has no explicit shutdown ownership.
- Only velocity ROS topics are active.
- The plugin reconstructs position by integrating velocity instead of consuming measured position.
- The plugin does not directly communicate with CAN, serial, or the LIMO base driver.
- Command direction parameters are not yet applied.
- More lifecycle cleanup and error reporting are needed before production hardware use.

## License

Apache License 2.0.
