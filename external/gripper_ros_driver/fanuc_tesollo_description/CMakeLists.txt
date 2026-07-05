cmake_minimum_required(VERSION 3.8)
project(fanuc_tesollo_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf config launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
