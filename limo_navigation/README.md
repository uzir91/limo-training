# limo_navigation

ROS 2 Humble mapping and localization bringup for the AgileX LIMO robot.

The package combines:

- `limo_simulation` bringup
- `robot_localization` EKF odometry
- SLAM Toolbox asynchronous mapping
- SLAM Toolbox localization
- Nav2 lifecycle managers for selecting mapping or localization mode
- RViz configuration for SLAM Toolbox tools

> This package does not launch the complete Nav2 planner, controller, behavior-tree navigator, or recovery stack.

## Current behavior

The current launch implementation is simulation-oriented:

- It always includes `limo_simulation/launch/simulation.launch.py`.
- Nodes in this launch file currently use simulation time.
- Both SLAM Toolbox nodes are created, but lifecycle autostart activates mapping when `mapping:=true` and localization when `mapping:=false`.

Real-hardware navigation bringup still needs a separate launch-path cleanup.

## Build

```bash
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to limo_navigation
source install/setup.bash
```

## Mapping

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  simulation:=true \
  mapping:=true
```

Headless mapping:

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  simulation:=true \
  mapping:=true \
  gui:=false \
  rviz:=false
```

Continue from a serialized SLAM Toolbox map:

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  mapping:=true \
  map_filename:=/absolute/path/to/serialized_map
```

## Localization

```bash
ros2 launch limo_navigation navigation.launch.py \
  namespace:=limo \
  simulation:=true \
  mapping:=false \
  map_filename:=/absolute/path/to/serialized_map
```

`map_filename` is passed to SLAM Toolbox as `map_file_name`. It refers to a serialized SLAM Toolbox map, not only a Nav2 map-server `.yaml` file.

## Launch arguments

| Argument | Default | Description |
| --- | --- | --- |
| `namespace` | `limo` | Robot namespace and frame prefix. |
| `simulation` | `true` | Passed to the included simulation launch. Current navigation nodes still use simulation time directly. |
| `gpu` | `default` | GPU environment selection for Gazebo and RViz. |
| `rviz` | `true` | Starts RViz. |
| `gui` | `true` | Controls the Gazebo graphical client. |
| `mapping` | `true` | `true` activates SLAM mapping; `false` activates localization. |
| `map_filename` | empty | Serialized SLAM Toolbox map path/name. |
| `ekf_odom_filename` | `ekf_odom.yaml` | EKF configuration filename. |
| `slam_filename` | `slam.yaml` | Mapping configuration filename. |
| `localization_filename` | `localization.yaml` | Localization configuration filename. |
| `rviz_filename` | `simulation.rviz` | Preferred RViz filename; falls back to `navigation.rviz` if missing. |

The launch file also supports explicit `ekf_odom_path`, `slam_path`, `localization_path`, and `rviz_path` overrides.

## Namespaced configuration

The launch file first checks:

```text
config/<namespace>/
```

For example:

```text
config/limo/ekf_odom.yaml
config/limo/slam.yaml
config/limo/localization.yaml
```

When a namespaced file is absent, it falls back to the default file under `config/`.

## Main topic flow

```text
/limo/odom/filtered
  + /limo/imu/filtered
  -> /limo/odom_ekf/filtered

/limo/scan/data
  + TF
  + odometry
  -> SLAM Toolbox map/localization
```

The EKF frame parameters are rewritten for the selected namespace:

```text
<namespace>/odom
<namespace>/base_footprint
```

## Useful checks

```bash
ros2 lifecycle get /limo/slam_node
ros2 lifecycle get /limo/localization_node
ros2 topic echo /limo/odom_ekf/filtered
ros2 topic echo /map
ros2 run tf2_ros tf2_echo limo/odom limo/base_footprint
```

Depending on how SLAM Toolbox resolves global map topics in the installed version, inspect the actual map topic with:

```bash
ros2 topic list | grep map
```

## License

Apache License 2.0.
