# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Geese_UI.py'],
    pathex=[],
    binaries=[
        # 添加pyzbar需要的DLL文件
        ('C:\\Users\\admin\\.conda\\envs\\DICK\\Lib\\site-packages\\pyzbar\\libzbar-64.dll', '.'),
        ('C:\\Users\\admin\\.conda\\envs\\DICK\\Lib\\site-packages\\pyzbar\\libiconv.dll', '.'),
    ],
    datas=[
        ('Geese.ico', '.'),  # 包含图标文件
        ('geese32.ico', '.'),  # 包含32x32小图标文件
        # 添加qrdet模型文件
        ('C:\\Users\\admin\\.conda\\envs\\DICK\\Lib\\site-packages\\qrdet\\.model\\qrdet-s.pt', 'qrdet\\.model'),
        ('C:\\Users\\admin\\.conda\\envs\\DICK\\Lib\\site-packages\\qrdet\\.model\\current_release.txt', 'qrdet\\.model'),
    ],
    hiddenimports=[
        # 基础库
        'os',
        'sys',
        'json',
        'threading',
        'time',
        'datetime',
        'subprocess',
        'psutil',
        
        # GUI相关
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        
        # 数据处理
        'numpy',
        
        # 图像处理
        'cv2',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        
        # 图表
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends.backend_tkagg',
        
        # 网络请求
        'requests',
        
        # QR码相关
        'pyzbar',
        'pyzbar.pyzbar',
        'zxingcpp',
        'qreader',
        'qrdet',
        'qrdet._qrdet_helpers',
        'quadrilateral_fitter',
        'shapely',
        'shapely.geometry',
        'shapely.ops',
        'ultralytics',
        
        # PyTorch相关 (ultralytics依赖)
        'torch',
        'torchvision',
        
        # 文件监控
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        
        # Web服务器
        'flask',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        # 排除不需要的大型库
        'sklearn',
        'sklearn.*',
        'tensorflow',
        'tensorflow.*',
        'theano',
        'theano.*',
        'jupyter',
        'jupyter.*',
        'notebook',
        'notebook.*',
        'ipython',
        'ipython.*',
        'spyder',
        'spyder.*',
        'pycharm',
        'pycharm.*',
        'pytest',
        'pytest.*',
        'django',
        'django.*',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Geese监控系统',  # 修改应用名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 禁用控制台，隐藏CMD窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Geese.ico' if os.path.exists('Geese.ico') else 'NONE',
    version='version_info.txt' if os.path.exists('version_info.txt') else None
)