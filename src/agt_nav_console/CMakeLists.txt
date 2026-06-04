cmake_minimum_required(VERSION 3.8)
project(agt_nav_console)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

add_executable(agt_nav_console_node
  src/agt_nav_console_node.cpp
)

add_executable(safety_guard_node
  src/safety_guard_node.cpp
)

add_executable(obstacle_stop_node
  src/obstacle_stop_node.cpp
)

target_include_directories(agt_nav_console_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(agt_nav_console_node
  rclcpp
)

ament_target_dependencies(safety_guard_node
  geometry_msgs
  rclcpp
  std_msgs
  std_srvs
)

ament_target_dependencies(obstacle_stop_node
  rclcpp
  sensor_msgs
  std_msgs
)

install(TARGETS
  agt_nav_console_node
  obstacle_stop_node
  safety_guard_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  include/
  DESTINATION include
)

install(DIRECTORY
  launch
  config
  scripts
  DESTINATION share/${PROJECT_NAME}
)

install(FILES
  README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
