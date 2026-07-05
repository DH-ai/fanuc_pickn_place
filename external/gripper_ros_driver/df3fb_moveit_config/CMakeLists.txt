cmake_minimum_required(VERSION 3.8)
project(df3fb_moveit_config)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch srdf rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/setup_planning_scene.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
