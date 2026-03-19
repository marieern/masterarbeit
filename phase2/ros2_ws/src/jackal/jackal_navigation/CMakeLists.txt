cmake_minimum_required(VERSION 3.5)
project(jackal_navigation)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
# Diese Pakete sind für den Build nicht zwingend nötig, schaden aber nicht
find_package(nav2_bringup REQUIRED)
find_package(slam_toolbox REQUIRED)

# WICHTIG: Hier werden Ihre Configs (YAML) und Launch-Files installiert
install(DIRECTORY config launch maps
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
