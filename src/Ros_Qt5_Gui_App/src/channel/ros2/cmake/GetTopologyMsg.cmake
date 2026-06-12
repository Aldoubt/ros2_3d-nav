include(FetchContent)

message(STATUS "get topology_msgs ...")

get_filename_component(PROJECT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../.." ABSOLUTE)
set(topology_msgs_LOCAL_SOURCE_DIR "${PROJECT_ROOT}/topology_msgs")
set(topology_msgs_DOWNLOAD_URL
    "https://github.com/chengyangkj/topology_msgs/archive/refs/heads/main.zip"
    CACHE STRING "")

if(EXISTS "${topology_msgs_LOCAL_SOURCE_DIR}/CMakeLists.txt")
  message(STATUS "use local topology_msgs from ${topology_msgs_LOCAL_SOURCE_DIR}")
  FetchContent_Declare(
    topology_msgs
    SOURCE_DIR "${topology_msgs_LOCAL_SOURCE_DIR}")
else()
  FetchContent_Declare(
    topology_msgs
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    URL "${topology_msgs_DOWNLOAD_URL}")
endif()

FetchContent_GetProperties(topology_msgs)
if(NOT topology_msgs_POPULATED)
  FetchContent_MakeAvailable(topology_msgs)
  
  set(TOPOLOGY_MSGS_TARGETS
    topology_msgs__rosidl_generator_cpp
    topology_msgs__rosidl_typesupport_cpp
    topology_msgs__rosidl_typesupport_fastrtps_cpp
    topology_msgs__rosidl_typesupport_introspection_cpp
  )
  
  foreach(TARGET_NAME ${TOPOLOGY_MSGS_TARGETS})
    if(TARGET ${TARGET_NAME})
      set_target_properties(${TARGET_NAME} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
      )
      
      install(TARGETS ${TARGET_NAME}
        RUNTIME DESTINATION bin/lib
        LIBRARY DESTINATION bin/lib
        ARCHIVE DESTINATION bin/lib
      )
    endif()
  endforeach()
endif()

# import targets:
# topology_msgs::topology_msgs 
