export const qaData = [
  {
    question: "What is WHEELTEC H30 INS module?",
    answer: "WHEELTEC H30 is a high-performance inertial navigation system (INS) module that integrates a 6-axis IMU sensor, providing accurate attitude, heading, and navigation data. It supports multiple communication interfaces including serial port, Ethernet, and I2C, and is compatible with ROS1/ROS2."
  },
  {
    question: "How to install the CH9102 driver?",
    answer: "1. Download the CH9102 driver package from the software tools folder. 2. Unzip the package and run the installer. 3. Connect the H30 module via USB, Windows will automatically recognize and install the driver. 4. Check Device Manager to confirm successful installation (you should see CH9102 USB-Serial device)."
  },
  {
    question: "What communication protocols does H30 support?",
    answer: "H30 supports multiple communication protocols: 1. Serial UART (TTL level) 2. Ethernet (TCP/UDP) 3. I2C/SPI interface 4. Custom YIS communication protocol for high-frequency data transmission"
  },
  {
    question: "How to perform magnetic field calibration?",
    answer: "Magnetic field calibration steps: 1. Use YIS Manager software to enter calibration mode. 2. Hold the H30 module and rotate it slowly in 8-shaped patterns for 2-3 minutes. 3. Ensure the module covers all orientations during rotation. 4. Save the calibration parameters. Detailed instructions are in the 'YIS系列产品磁场校准用户手册.pdf'."
  },
  {
    question: "What is the output data format of H30?",
    answer: "H30 outputs data in the YIS protocol format, which includes: 1. Attitude data (pitch, roll, yaw) 2. Angular velocity 3. Acceleration 4. Magnetic field data 5. GPS data (if available). See 'YIS数据协议例程说明.pdf' for detailed protocol format."
  },
  {
    question: "How to use H30 with ROS?",
    answer: "ROS integration steps: 1. Install ROS1 or ROS2 according to your system. 2. Download the ROS SDK from the '2.ROS_SDK' folder. 3. Compile the ROS package: catkin_make (ROS1) or colcon build (ROS2). 4. Run the driver node. 5. Visualize data using RViz. For detailed instructions, refer to the README file in the ROS SDK folder."
  },
  {
    question: "What is the difference between H30 and H30mini?",
    answer: "Main differences: 1. H30mini is a compact version with smaller size. 2. H30mini supports Ethernet interface natively. 3. H30 has additional RS485 option. 4. Both use the same YIS106 chip and offer similar performance. Refer to respective user manuals for detailed specifications."
  },
  {
    question: "How to upgrade H30 firmware?",
    answer: "Firmware upgrade steps: 1. Use YIS Manager software. 2. Connect H30 via USB or Ethernet. 3. Select 'Firmware Upgrade' in the software. 4. Choose the firmware file (.bin). 5. Click upgrade and wait for completion. Note: Do not disconnect during upgrade. See user manual for detailed firmware upgrade instructions."
  },
  {
    question: "What is the default baud rate of H30?",
    answer: "Default baud rate is 921600 bps for serial communication. You can modify it using NetModuleConfig tool or YIS Manager software. Available baud rates: 9600, 115200, 460800, 921600, etc."
  },
  {
    question: "How to set the IP address of H30 Ethernet?",
    answer: "1. Use NetModuleConfig tool to scan for H30 devices on the network. 2. Select the target device. 3. Modify IP address, subnet mask, and gateway. 4. Click 'Apply' to save settings. Default IP is usually 192.168.1.100."
  }
];
