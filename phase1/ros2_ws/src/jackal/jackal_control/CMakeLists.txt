cmake_minimum_required(VERSION 3.5)
project(jackal_control)


find_package(ament_cmake REQUIRED)


# Korrigierter Pfad: src/ statt scripts/
install(PROGRAMS
  src/gps_gatekeeper.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY 
  config 
  launch 
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
