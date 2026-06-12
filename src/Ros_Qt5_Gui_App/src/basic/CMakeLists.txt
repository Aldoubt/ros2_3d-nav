add_library(basic INTERFACE)

target_include_directories(basic INTERFACE 
${CMAKE_CURRENT_SOURCE_DIR}
algorithm
map
point
common
)

if(WIN32)
  target_link_libraries(basic INTERFACE Eigen3::Eigen yaml-cpp::yaml-cpp common Qt5::Gui)
else()
  target_link_libraries(basic INTERFACE Eigen3::Eigen yaml-cpp::yaml-cpp common Qt5::Gui)
endif()
