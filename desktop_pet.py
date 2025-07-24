import glob
from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QVBoxLayout, QLineEdit, QTextEdit, QApplication
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QFont, QTransform
from api_client import ApiWorker, ApiClient

class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        # API客户端初始化
        self.api_client = ApiClient(
            api_key="sk-e6888adc03d048b498e15f63524b7549",
            base_url="https://api.deepseek.com",
            history_file="chat_history.json"
        )
        
        # 初始化变量
        self.input_dialog = None
        self.output_dialog = None
        self.api_worker = None
        self.output_timer = None  # 输出框自身的自动关闭定时器
        self.leave_hover_timer = None  # 离开桌宠后的延迟关闭定时器
        self.is_viewing_history = False
        self.is_dragging = False  # 标记是否正在拖动
        
        # 移动与位置相关参数
        self.speed = 5 # 移动速度（像素/帧）
        self.direction = 1  # 1:向右，-1:向左
        self.screen_geometry = QApplication.desktop().availableGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_mid = self.screen_width // 2  # 屏幕中线（左右分界）
        self.is_moving = True  # 移动状态标记
        
        # 初始化UI和动画
        self.initUI()
        self.loadAnimations()
        self.setupAnimation()

    def initUI(self):
        # 窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 桌宠尺寸
        self.pet_width = 255
        self.pet_height = 255
        
        # 初始位置：左下角（留出20px边距）
        screen_height = self.screen_geometry.height()
        self.start_x = 20  # 左边距
        self.start_y = screen_height - self.pet_height - 20  # 底边距
        self.setGeometry(self.start_x, self.start_y, self.pet_width, self.pet_height)

        # 宠物显示标签
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.pet_width, self.pet_height)
        self.setCentralWidget(self.label)

        # 鼠标跟踪
        self.is_hovered = False
        self.setMouseTracking(True)

    def loadAnimations(self):
        # 加载动画帧
        self.move_frames = [QPixmap(f) for f in sorted(glob.glob("移动/*.png"))]
        self.interact_frames = [QPixmap(f) for f in sorted(glob.glob("互动/*.png"))]
        if not self.move_frames or not self.interact_frames:
            raise FileNotFoundError("请确保'移动'和'互动'文件夹中包含PNG图片")

    def setupAnimation(self):
        # 动画和移动定时器（每50ms更新一次）
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)
        self.timer.start(50)

    def updateAnimation(self):
        # 1. 处理水平移动（仅当移动状态为True且不在拖动时）
        if self.is_moving and not self.is_dragging:
            self.move_horizontally()
        
        # 2. 处理动画帧（根据方向翻转贴图）
        if self.is_hovered:
            frames = self.interact_frames
        else:
            frames = self.move_frames
        
        if frames:
            self.current_frame = (self.current_frame + 1) % len(frames)
            current_pixmap = frames[self.current_frame]
            
            # 根据移动方向翻转贴图
            if self.direction == -1:
                transform = QTransform()
                transform.scale(-1, 1)  # 水平翻转
                current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)
            
            self.label.setPixmap(current_pixmap.scaled(
                self.pet_width, self.pet_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def move_horizontally(self):
        # 计算新位置
        current_x = self.x()
        new_x = current_x + self.speed * self.direction
        
        # 边界检测（左右边缘）
        if new_x <= 0:  # 左边缘
            new_x = 0
            self.direction = 1  # 转向右
        elif new_x + self.pet_width >= self.screen_width:  # 右边缘
            new_x = self.screen_width - self.pet_width
            self.direction = -1  # 转向左
        
        # 更新位置
        self.move(new_x, self.y())

    def enterEvent(self, event):
        # 鼠标悬停桌宠：停止移动，切换动画，停止离开悬停定时器
        self.is_hovered = True
        self.is_moving = False
        self.current_frame = 0
        
        # 停止离开悬停定时器（如果正在运行）
        if self.leave_hover_timer and self.leave_hover_timer.isActive():
            self.leave_hover_timer.stop()

    def leaveEvent(self, event):
        # 离开桌宠悬停：恢复移动，关闭输入框
        self.is_hovered = False
        self.is_moving = True
        self.current_frame = 0
        
        # 立即关闭输入框
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()
            self.input_dialog = None
            
        # 输出框存在时，启动5秒延迟关闭定时器（如果不在输出框上）
        if self.output_dialog and self.output_dialog.isVisible():
            # 检查鼠标是否在输出框上（通过判断输出框是否有焦点相关状态）
            if not self.output_dialog.underMouse():
                if self.leave_hover_timer:
                    self.leave_hover_timer.stop()
                self.leave_hover_timer = QTimer(self)
                self.leave_hover_timer.timeout.connect(self.closeOutputDialog)
                self.leave_hover_timer.start(5000)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()
            self.is_dragging = False  # 初始标记为未拖动
            
            # 如果输出框可见，立即关闭它
            if self.output_dialog and self.output_dialog.isVisible():
                self.closeOutputDialog()
            
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # 标记为正在拖动
            self.is_dragging = True
            # 拖动桌宠
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()
            
            # 同步移动输入框
            if self.input_dialog and self.input_dialog.isVisible():
                dialog_x = self.get_side_position(self.input_width)
                self.input_dialog.move(dialog_x, self.input_dialog.y())
                
            # 同步移动输出框（随桌宠水平移动）
            if self.output_dialog and self.output_dialog.isVisible():
                dialog_x = self.get_side_position(self.output_width)
                self.output_dialog.move(dialog_x, self.get_output_y_position())
            
            event.accept()

    def mouseReleaseEvent(self, event):
        # 鼠标释放时检查是否是点击（非拖动）
        if event.button() == Qt.LeftButton:
            # 如果不是拖动状态且处于悬停状态，才显示输入框
            if not self.is_dragging and self.is_hovered:
                self.showInputDialog()
            # 重置拖动状态
            self.is_dragging = False
            event.accept()

    def get_side_position(self, base_width):
        """计算对话框的X坐标位置（左右侧自动切换）"""
        pet_center_x = self.geometry().x() + self.pet_width // 2  # 桌宠中心点X坐标
        
        if pet_center_x < self.screen_mid:
            # 左半边：对话框在桌宠右侧
            return self.geometry().x() + self.pet_width + 10  # 右侧+10px间距
        else:
            # 右半边：对话框在桌宠左侧
            return self.geometry().x() - base_width - 10  # 左侧-宽度-10px间距

    def get_output_y_position(self):
        """计算输出框Y坐标（桌宠头顶位置）"""
        return self.geometry().y() - self.output_height - 10  # 桌宠顶部向上10px

    def showInputDialog(self):
        # 如果输入框已存在，先关闭
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()

        self.input_dialog = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
        self.input_dialog.setStyleSheet("""
            background-color: rgba(169, 84, 84, 50);
            border: 1px solid rgba(222, 116, 135, 100);
            border-radius: 5px;
        """)
        
        layout = QVBoxLayout()
        input_box = QLineEdit(self.input_dialog)
        input_box.setPlaceholderText("输入内容")
        
        font = QFont()
        font.setFamily("SimSun")
        font.setPointSize(10)
        input_box.setFont(font)
        
        input_box.setStyleSheet("""
            background-color: rgba(169, 84, 84, 80);
            border: 2px solid rgba(255, 255, 255, 150);
            padding: 8px;
            border-radius: 3px;
            color: #FFFFFF;
        """)
        input_box.returnPressed.connect(
            lambda: self.submitToDeepSeek(input_box.text(), self.input_dialog)
        )
        
        layout.addWidget(input_box)
        self.input_dialog.setLayout(layout)
        
        # 输入框尺寸和位置
        self.input_width = 350
        self.input_height = 100
        dialog_x = self.get_side_position(self.input_width)
        dialog_y = self.geometry().y() + 10  # Y坐标固定在桌宠上方+10px
        self.input_dialog.setGeometry(dialog_x, dialog_y, self.input_width, self.input_height)
        self.input_dialog.show()

    def submitToDeepSeek(self, text, dialog):
        if not text.strip():
            dialog.close()
            self.input_dialog = None
            return

        dialog.close()
        self.input_dialog = None
        
        if text.strip() == "查看历史":
            self.is_viewing_history = True
            history_text = self.api_client.get_history_text()
            self.showOutputDialog(history_text)
            return
        
        self.is_viewing_history = False
        self.api_worker = ApiWorker(
            self.api_client.client, 
            text, 
            self.api_client.history_file
        )
        self.api_worker.result_ready.connect(
            lambda response: self.handle_api_response(text, response)
        )
        self.api_worker.start()
    
    def handle_api_response(self, user_input, response):
        self.api_client.save_to_history(user_input, response)
        self.showOutputDialog(response)
        self.api_worker = None

    def showOutputDialog(self, text):
        if self.output_dialog and self.output_dialog.isVisible():
            self.output_dialog.close()

        self.output_dialog = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
        self.output_dialog.setStyleSheet("""
            background-color: rgba(222, 136, 135, 50);
            border: 1px solid rgba(70, 130, 180, 100);
            border-radius: 5px;
        """)
        self.output_dialog.setMouseTracking(True)
        # 绑定输出框的鼠标事件
        self.output_dialog.enterEvent = self.on_output_enter
        self.output_dialog.leaveEvent = self.on_output_leave
        
        layout = QVBoxLayout()
        output_text = QTextEdit(self.output_dialog)
        output_text.setReadOnly(True)
        output_text.setText(text)
        output_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        font = QFont()
        font.setFamily("SimSun")
        font.setPointSize(10)
        output_text.setFont(font)
        
        output_text.setStyleSheet("""
            background-color: transparent;
            border: none;
            padding: 5px;
            color: #FFFFFF;
        """)
        
        layout.addWidget(output_text)
        self.output_dialog.setLayout(layout)
        
        # 输出框尺寸
        if self.is_viewing_history:
            self.output_width = int(self.input_width * 1.5)
            max_output_height = 400
        else:
            self.output_width = self.input_width
            max_output_height = 400
        
        # 确保输出框不超出屏幕顶部
        screen_top = 20  # 顶部留20px边距
        self.output_height = max_output_height
        
        # 计算X坐标（左/右取决于桌宠位置）
        dialog_x = self.get_side_position(self.output_width)
        # 计算Y坐标（桌宠头顶）
        dialog_y = self.get_output_y_position()
        
        # 如果顶部空间不足，调整位置到桌宠下方
        if dialog_y < screen_top:
            dialog_y = self.geometry().y() + self.pet_height + 10  # 桌宠下方+10px
        
        self.output_dialog.setGeometry(dialog_x, dialog_y, self.output_width, self.output_height)
        self.output_dialog.show()
        
        # 启动输出框自身的自动关闭定时器（默认8秒/15秒）
        self.start_output_timer(15000 if self.is_viewing_history else 8000)

    def start_output_timer(self, duration):
        # 停止已有定时器
        if self.output_timer:
            self.output_timer.stop()
        # 启动新定时器
        self.output_timer = QTimer(self)
        self.output_timer.timeout.connect(self.closeOutputDialog)
        self.output_timer.start(duration)

    def on_output_enter(self, event):
        """鼠标进入输出框时：停止所有关闭定时器"""
        # 停止输出框自身的定时器
        if self.output_timer and self.output_timer.isActive():
            self.output_timer.stop()
        # 停止离开桌宠后的延迟定时器
        if self.leave_hover_timer and self.leave_hover_timer.isActive():
            self.leave_hover_timer.stop()

    def on_output_leave(self, event):
        """鼠标离开输出框时：直接关闭输出框（核心修改）"""
        self.closeOutputDialog()

    def closeOutputDialog(self):
        # 关闭输出框并清理所有定时器
        if self.output_dialog:
            self.output_dialog.close()
            self.output_dialog = None
        
        # 停止所有相关定时器
        if self.output_timer:
            self.output_timer.stop()
            self.output_timer = None
        if self.leave_hover_timer:
            self.leave_hover_timer.stop()
            self.leave_hover_timer = None
        
        self.is_viewing_history = False