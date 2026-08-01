cmake_minimum_required(VERSION 3.8)
project(limo_simulation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ros_gz_sim REQUIRED)
find_package(ros_gz_bridge REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(controller_manager REQUIRED)
find_package(joy REQUIRED)
find_package(teleop_twist_joy REQUIRED)
find_package(imu_complementary_filter REQUIRED)
find_package(safety_imu REQUIRED)
find_package(safety_hardware REQUIRED)
find_package(twist_mux REQUIRED)
find_package(image_throttle REQUIRED)
find_package(apriltag_ros REQUIRED)
find_package(apriltag_pose REQUIRED)
find_package(audio_capture REQUIRED)
find_package(audio_play REQUIRED)
find_package(sound_play REQUIRED)
find_package(sr_vosk REQUIRED)
find_package(tts_piper REQUIRED)
find_package(ocr_tesseract REQUIRED)
find_package(traffic_light REQUIRED)
find_package(rviz2 REQUIRED)
find_package(limo_description REQUIRED)

install(
  DIRECTORY
    config
    launch
    rviz
    urdf
    worlds
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
