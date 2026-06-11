cmake_minimum_required(VERSION 3.0.2)
project(cartographer_ld06)

find_package(catkin REQUIRED)

catkin_package()

install(DIRECTORY launch configuration_files
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
