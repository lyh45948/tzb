import { Document } from './types';

export const documents: Document[] = [
  // User Manuals
  {
    id: 'pdf-1',
    name: 'WHEELTEC_H30惯导模块用户手册_20251025.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/1.WHEELTEC_H30惯导模块用户手册_20251025.pdf',
    description: 'WHEELTEC H30 INS Module User Manual - Complete guide for H30 INS module usage'
  },
  {
    id: 'pdf-2',
    name: 'YIS106芯片产品手册.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/2.YIS106芯片产品手册.pdf',
    description: 'YIS106 Chip Product Manual'
  },
  {
    id: 'pdf-3',
    name: 'YIS Manager上位机使用说明.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/3.YIS Manager上位机使用说明.pdf',
    description: 'YIS Manager PC Software User Guide'
  },
  {
    id: 'pdf-4',
    name: 'YIS通讯协议.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/4.YIS通讯协议.pdf',
    description: 'YIS Communication Protocol'
  },
  {
    id: 'pdf-5',
    name: 'YIS数据协议例程说明.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/5.YIS数据协议例程说明.pdf',
    description: 'YIS Data Protocol Example Explanation'
  },
  {
    id: 'pdf-6',
    name: 'YIS系列产品磁场校准用户手册.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/6.YIS系列产品磁场校准用户手册.pdf',
    description: 'YIS Series Magnetic Field Calibration User Manual'
  },
  {
    id: 'pdf-7',
    name: 'INS科普文档.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/7.INS科普文档.pdf',
    description: 'INS Popular Science Document'
  },
  {
    id: 'pdf-8',
    name: 'WHEELTEC_网口H30mini惯导模块用户手册_20250515.pdf',
    category: 'userManual',
    type: 'pdf',
    path: '1.用户手册/8.WHEELTEC_网口H30mini惯导模块用户手册_20250515.pdf',
    description: 'WHEELTEC Ethernet H30mini INS Module User Manual'
  },
  
  // Software Tools
  {
    id: 'zip-1',
    name: 'YIS Manager V2.8.7.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/1.YIS Manager V2.8.7.zip',
    description: 'YIS Manager Software V2.8.7'
  },
  {
    id: 'zip-2',
    name: '串口助手.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/2.串口助手.zip',
    description: 'Serial Port Assistant Tool'
  },
  {
    id: 'zip-3',
    name: 'CH9102驱动与资料.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/3.CH9102驱动与资料.zip',
    description: 'CH9102 Driver and Documentation'
  },
  {
    id: 'zip-4',
    name: 'CH9102修改串口号工具.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/4.CH9102修改串口号工具（除串口serial号其它不可修改！！）.zip',
    description: 'CH9102 Serial Number Modification Tool'
  },
  {
    id: 'zip-5',
    name: 'wireshark网络抓包工具.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/5.wireshark网络抓包工具.zip',
    description: 'Wireshark Network Packet Capture Tool'
  },
  {
    id: 'zip-6',
    name: 'NetModuleConfig网口IP_波特率修改工具.zip',
    category: 'softwareTools',
    type: 'zip',
    path: '3.软件工具/6.NetModuleConfig网口IP_波特率修改工具.zip',
    description: 'NetModuleConfig Ethernet IP & Baud Rate Modification Tool'
  },
  
  // Chip Manuals & Schematics
  {
    id: 'pdf-9',
    name: 'H30原理图_2026-01-07.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/H30原理图_2026-01-07.pdf',
    description: 'H30 Schematic Diagram'
  },
  {
    id: 'pdf-10',
    name: 'WHEELTEC_H30_Mini位号图.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/WHEELTEC_H30_Mini位号图.pdf',
    description: 'WHEELTEC H30 Mini Reference Designator Diagram'
  },
  {
    id: 'pdf-11',
    name: 'WHEELTEC_H30_Mini原理图.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/WHEELTEC_H30_Mini原理图.pdf',
    description: 'WHEELTEC H30 Mini Schematic Diagram'
  },
  {
    id: 'pdf-12',
    name: 'WHEELTEC_H30_PCB_带485.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/WHEELTEC_H30_PCB_带485.pdf',
    description: 'WHEELTEC H30 PCB with RS485'
  },
  {
    id: 'pdf-13',
    name: 'WHEELTEC_H30_PCB_无485.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/WHEELTEC_H30_PCB_无485.pdf',
    description: 'WHEELTEC H30 PCB without RS485'
  },
  {
    id: 'pdf-14',
    name: 'WHEELTEC_H30位号图.pdf',
    category: 'chipManual',
    type: 'pdf',
    path: '4.芯片手册、原理图、PCB封装/WHEELTEC_H30位号图.pdf',
    description: 'WHEELTEC H30 Reference Designator Diagram'
  },
  
  // Mechanical Models
  {
    id: 'pdf-15',
    name: 'WHEELTEC_H30尺寸图.pdf',
    category: 'mechanicalModels',
    type: 'pdf',
    path: '5.机械模型文件/WHEELTEC_H30尺寸图.pdf',
    description: 'WHEELTEC H30 Dimension Drawing'
  },
  {
    id: 'stp-1',
    name: 'WHEELTEC_H30传感器（金属外壳）.stp',
    category: 'mechanicalModels',
    type: 'zip',
    path: '5.机械模型文件/WHEELTEC_H30传感器（金属外壳）.stp',
    description: 'WHEELTEC H30 Sensor (Metal Enclosure) 3D Model'
  },
  {
    id: 'stp-2',
    name: 'WHEELTEC_H30裸板.stp',
    category: 'mechanicalModels',
    type: 'zip',
    path: '5.机械模型文件/WHEELTEC_H30裸板.stp',
    description: 'WHEELTEC H30 Bare Board 3D Model'
  },
  
  // Contact
  {
    id: 'pdf-16',
    name: '联系我们.pdf',
    category: 'contactUs',
    type: 'pdf',
    path: '联系我们.pdf',
    description: 'Contact Us Information'
  },
  
  // Update Log
  {
    id: 'txt-1',
    name: '更新说明.txt',
    category: 'updateLog',
    type: 'code',
    path: '更新说明.txt',
    description: 'Update Log and Version History',
    language: 'text'
  }
];
