cmake_minimum_required(VERSION 3.8)
project(mid360_nav_demo)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(PCL REQUIRED COMPONENTS common filters io registration)
find_package(pcl_conversions REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)

add_executable(icp_relocalizer_node src/icp_relocalizer_node.cpp)
target_include_directories(icp_relocalizer_node PRIVATE ${PCL_INCLUDE_DIRS})
ament_target_dependencies(icp_relocalizer_node
  geometry_msgs
  nav_msgs
  pcl_conversions
  rclcpp
  sensor_msgs
  std_msgs
  tf2
  tf2_ros
)
target_link_libraries(icp_relocalizer_node ${PCL_LIBRARIES})

install(TARGETS
  icp_relocalizer_node
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/octomap_tuning_gui.py
  scripts/sim_drive_gui.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  config
  maps
  rviz
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
