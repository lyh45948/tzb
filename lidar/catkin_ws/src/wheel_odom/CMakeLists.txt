cmake_minimum_required(VERSION 3.0.2)
project(wheel_odom)

find_package(catkin REQUIRED COMPONENTS
  rospy
  nav_msgs
  geometry_msgs
  tf2_ros
  tf
)

catkin_package(
  CATKIN_DEPENDS rospy nav_msgs geometry_msgs tf2_ros tf
)

catkin_install_python(PROGRAMS
  scripts/wheel_odom_publisher.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)
