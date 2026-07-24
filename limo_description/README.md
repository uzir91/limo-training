# limo_description

Robot-description package for the AgileX LIMO platform on ROS 2 Humble.

The package contains the LIMO URDF/Xacro model, meshes, wheel joints, IMU, lidar, depth-camera model, `ros2_control` integration point, robot-state publisher launch file, and RViz configuration.

## Contents

```text
config/   Default controller configuration used by the description
launch/   Robot-description and RViz bringup
meshes/   LIMO base and wheel mesh files
rviz/     RViz display configuration
urdf/     Robot, wheel, sensor, and ros2_control Xacro files
```

The assembled model is defined in:

```text
urdf/assembly.xacro
```

## Build

From the workspace root:

```bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select limo_description
source install/setup.bash
```

## Launch

```bash
ros2 launch limo_description description.launch.py
```

Default namespace:

```text
limo
```

Example without a namespace:

```bash
ros2 launch limo_description description.launch.py namespace:=
```

Example for simulation time without RViz:

```bash
ros2 launch limo_description description.launch.py \
  namespace:=limo \
  simulation:=true \
  rviz:=false \
  joint_state:=false
```

## Launch arguments

| Argument | Default | Description |
| --- | --- | --- |
| `namespace` | `limo` | Namespace and frame prefix used by the model. |
| `gpu` | `default` | Use `nvidia` for NVIDIA PRIME render-offload variables; other values use `DRI_PRIME=1`. |
| `simulation` | `false` | Enables simulation time for published nodes. |
| `rviz` | `true` | Starts RViz. |
| `joint_state` | `true` | Starts a joint-state publisher. |
| `joint_state_gui` | `true` | Uses `joint_state_publisher_gui`; otherwise uses `joint_state_publisher`. |
| `controller_manager_path` | Package default | Controller YAML passed into the robot model. |
| `ros2_control_path` | Package default | Selects the Xacro file that defines the hardware backend. |

## Main model data

- Wheelbase: `0.1974 m`
- Wheel track: `0.176 m`
- Wheel radius: `0.0482 m`
- Wheel joints:
  - `wheel_front_left_joint`
  - `wheel_front_right_joint`
  - `wheel_rear_left_joint`
  - `wheel_rear_right_joint`

The sensor model includes:

- IMU
- YDLIDAR-compatible lidar model
- Dabai depth-camera model

## Notes

This package describes the robot but does not start Gazebo or a real hardware driver. Use `limo_simulation` for simulation and `limo_hardware` for real-hardware controller bringup.

## License

Apache License 2.0. See [LICENSE](LICENSE).
