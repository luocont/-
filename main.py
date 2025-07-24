import sys
import os
# 运行时清空对话历史文件
HISTORY_FILE = "chat_history.json"
if os.path.exists(HISTORY_FILE):
    os.remove(HISTORY_FILE)  # 删除历史文件（下次启动时会重新创建）

from PyQt5.QtWidgets import QApplication
from desktop_pet import DesktopPet

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())