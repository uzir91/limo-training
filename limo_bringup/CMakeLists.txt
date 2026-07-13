cmake_minimum_required(VERSION 3.8)
project(limo_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(controller_interface REQUIRED)
find_package(yaml_cpp_vendor REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(gazebo_ros QUIET) # Only if using Gazebo

add_library(${PROJECT_NAME}_node SHARED
  src/limo_bringup_node.cpp
)
target_include_directories(${PROJECT_NAME}_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
ament_target_dependencies(${PROJECT_NAME}_node
  rclcpp rclcpp_lifecycle hardware_interface pluginlib controller_interface yaml_cpp_vendor std_msgs sensor_msgs geometry_msgs
)
pluginlib_export_plugin_description_file(hardware_interface limo_bringup_plugin.xml)

# 1. Headers
install(DIRECTORY include/
  DESTINATION include
)

# 2. Libraries
install(TARGETS ${PROJECT_NAME}_node
  EXPORT export_${PROJECT_NAME}_node
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY description/urdf/
  DESTINATION share/${PROJECT_NAME}/description/urdf
)

install(DIRECTORY description/meshes/
  DESTINATION share/${PROJECT_NAME}/description/meshes
)

install(DIRECTORY description/ros2_control/
  DESTINATION share/${PROJECT_NAME}/description/ros2_control
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

install(DIRECTORY rviz/
  DESTINATION share/${PROJECT_NAME}/rviz
)

install(DIRECTORY worlds/
  DESTINATION share/${PROJECT_NAME}/worlds
)

install(FILES limo_bringup_plugin.xml
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
