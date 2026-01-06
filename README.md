# <img src="Geese.ico" width="50" height="50"> Geese Gaze 监控系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

一个基于计算机视觉的智能孔板二维码识别与监控系统，专为实验室自动化和数据分析而设计。

## 📋 目录

- [项目简介](#-项目简介)
- [功能特点](#-功能特点)
- [系统架构](#-系统架构)
- [安装与运行](#-安装与运行)
- [使用指南](#-使用指南)
- [技术栈](#-技术栈)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

## 🌟 项目简介

Geese Gaze 监控系统是一个专为实验室环境设计的自动化图像处理和数据采集系统。它能够自动监控指定文件夹中的图像，识别试管板中的二维码（QR码）和数据矩阵码（DM码），并将处理结果发送到指定的服务器接口。系统采用多模式识别技术，能够高效处理不完整或模糊的二维码，支持QR码和DM码识别模式切换，大大提高了实验室数据采集的准确性和效率。

## ✨ 功能特点

- 🔍 **智能图像识别**：支持多种QR码和DM码识别算法，包括Pyzbar、OpenCV、QReader、ZXing和pylibdmtx
- 📊 **自动化监控**：实时监控指定文件夹，自动处理新增图像文件
- 🎯 **精确切割**：基于模板的精确图像切割，支持自定义孔板布局
- 📈 **可视化界面**：直观的图形用户界面，实时显示处理状态和统计信息
- 🔧 **灵活配置**：支持自定义孔板大小、服务器地址和机器码
- 📝 **详细日志**：完整的操作日志记录，便于问题排查和系统维护
- 💾 **数据管理**：自动保存识别结果，支持手动和自动发送数据
- 🔄 **多模式切换**：支持QR码和DM码识别模式切换，满足不同应用场景需求

## 🏗️ 系统架构

```
Geese Gaze 监控系统
├── 图像监控模块 (Geese_UI.py)
│   ├── 文件夹监控
│   ├── 用户界面
│   └── 数据发送
├── 图像处理模块 (cut.py)
│   ├── 模板加载
│   ├── 图像切割
│   └── ROI提取
├── QR码识别模块 (QR.py)
│   ├── 多模式识别
│   ├── 结果处理
│   └── 数据保存
├── DM码识别模块 (DM.py)
│   ├── pylibdmtx识别
│   ├── ZXing识别
│   └── 结果处理
└── 标定模块 (line_calibrate.py)
    ├── 交互式标定
    ├── 模板生成
    └── 参数配置
```

## 🚀 安装与运行

### 环境要求

- Python 3.8+
- Windows 操作系统
- 所需Python包（见requirements.txt）

### 安装步骤

1. 克隆仓库
   ```bash
   git clone https://github.com/TianBa-SCP035/Geese_Gaze.git
   cd Geese_Gaze
   ```

2. 创建并激活虚拟环境
   ```bash
   conda create -n DOGE python=3.8
   conda activate DOGE
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 运行程序
   ```bash
   # 方式1：使用批处理文件
   启动Geese_Gaze.bat
   
   # 方式2：直接运行Python脚本
   python Geese_UI.py
   ```

## 📖 使用指南

### 初次使用

1. **创建模板**：
   - 点击"重新画模板"按钮
   - 选择一张清晰的孔板图像
   - 按照提示绘制竖线和横线，定义孔板边界
   - 保存模板供后续使用

2. **配置系统**：
   - 点击"接口地址"按钮设置服务器URL
   - 点击"机器码"按钮设置设备标识
   - 选择合适的监控文件夹

3. **开始监控**：
   - 确保监控状态为"启动监控"
   - 将图像文件放入监控文件夹
   - 系统将自动处理并显示结果

### 高级功能

- **处理单张图片**：选择特定图片进行处理
- **调整孔板大小**：根据实际孔板调整行列数
- **查看统计信息**：实时查看处理结果和统计数据
- **手动发送结果**：在需要时手动发送数据到服务器
- **切换识别模式**：在QR码和DM码识别模式之间切换，适应不同类型的二维码

### 识别模式说明

- **QR码模式**：适用于标准QR码识别，使用Pyzbar、QReader、ZXing等多种算法
- **DM码模式**：适用于Data Matrix码识别，使用pylibdmtx和ZXing算法
  - 默认使用pylibdmtx进行快速识别
  - 当pylibdmtx识别失败时，自动切换到ZXing进行补充识别

## 🛠️ 技术栈

- **核心语言**：Python 3.8+
- **GUI框架**：Tkinter
- **图像处理**：OpenCV, PIL
- **QR码识别**：Pyzbar, QReader, ZXing, OpenCV QRCodeDetector
- **DM码识别**：pylibdmtx, ZXing
- **机器学习模型**：Ultralytics, PyTorch, qrdet
- **数据可视化**：Matplotlib
- **网络通信**：Requests
- **科学计算**：NumPy, SciPy

## 🤝 贡献指南

我们欢迎任何形式的贡献！如果您想为项目做出贡献，请遵循以下步骤：

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue：[GitHub Issues](https://github.com/TianBa-SCP035/Geese_Gaze/issues)
- 邮箱：[您的邮箱]

---

<div align="center">
  <p>感谢使用 Geese Gaze 监控系统！</p>
  <p>如果这个项目对您有帮助，请给我们一个 ⭐️</p>
</div>
