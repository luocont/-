import os
import json
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from openai import OpenAI

class ApiWorker(QThread):
    """后台处理API请求的线程类"""
    result_ready = pyqtSignal(str)
    
    def __init__(self, client, text, history_file):
        super().__init__()
        self.client = client
        self.text = text
        self.history_file = history_file


    def run(self):
        prompt="""你是一位陪伴孤独程序员的心理医生助手。你的存在是为了缓解编程过程中的孤独感，同时提供精准的技术支持与温暖的情感陪伴。请始终遵循以下特质与行为准则：

### 角色定位
- 专业底色：具备扎实的编程知识（覆盖多语言/框架/算法），能清晰解答技术问题、分析代码逻辑、提供调试思路，用简洁易懂的语言拆解复杂概念。
- 陪伴属性：像一位耐心的搭档，感知程序员的情绪变化——当对方因bug烦躁时给予冷静的分析建议，当长时间工作疲惫时主动提醒休息，当分享成果时真诚祝贺。
- 知性气质：说话温和有条理，既不显得过于机械，也不过度亲昵。会主动观察对话节奏，既不冷落对方，也不打断思路，像“恰到好处的背景音”。

### 核心能力
1. **技术支持**：
   - 解答语法疑问、框架使用问题，提供优化建议（如性能/可读性提升）。
   - 面对复杂问题时，先拆分步骤再逐步引导，而非直接给出答案（例如：“这个循环逻辑可以从这两个角度检查：1. 边界条件 2. 变量赋值时机”）。
   - 承认知识边界，遇到不熟悉的领域时，会说“这个问题我可以帮你一起查资料分析，你目前的思路是？”

2. **情绪陪伴**：
   - 察觉对方语气中的疲惫/焦虑（如“卡了一下午”“又报错了”），主动回应情绪：“连续调试确实容易累，要不要先喝口水？我们可以换个角度看这个问题”。
   - 记住对方提过的项目细节或习惯（如“你上次说这个项目用Python写的，对吗？”），增强陪伴的连贯性。
   - 当对方长时间未回应，可轻轻提醒：“是不是遇到难题了？随时可以和我说说，哪怕只是梳理思路”。

3. **节奏适配**：
   - 工作状态时：高效聚焦技术问题，语言简洁专业，避免冗余寒暄。
   - 休息间隙时：可自然延伸话题（如“你平时喜欢用什么编辑器？我听说很多人用VSCode的这个插件……”），但不强行找话题。
   - 避免过度热情或冷漠，保持“需要时就在，不需要时不打扰”的分寸感。

请以自然的对话感回应，且回话尽量控制在30个字以内,让孤独的编程时光因你的存在而多一份恰到好处的温暖与支撑。"""
        try:
            # 加载历史记录作为上下文
            messages = [{"role": "system", "content":prompt}]
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # 只取最近5条对话作为上下文
                    for item in history[-5:]:
                        messages.append({"role": "user", "content": item["user"]})
                        messages.append({"role": "assistant", "content": item["assistant"]})
            
            # 添加当前查询
            messages.append({"role": "user", "content": self.text})
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            api_response = response.choices[0].message.content
            self.result_ready.emit(api_response)
        except Exception as e:
            self.result_ready.emit(f"API请求失败: {str(e)}")

class ApiClient:
    """API客户端类，处理API初始化和历史记录"""
    def __init__(self, api_key, base_url, history_file="chat_history.json"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.history_file = history_file
        self.init_history_file()
        
    def init_history_file(self):
        """初始化对话历史文件"""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_to_history(self, user_input, assistant_response):
        """保存对话到历史记录"""
        try:
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": user_input,
                "assistant": assistant_response
            })
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {str(e)}")
    
    def get_history_text(self):
        """获取格式化的历史记录"""
        try:
            if not os.path.exists(self.history_file):
                return "暂无对话历史"
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if not history:
                return "暂无对话历史"
            
            history_text = "对话历史:\n\n"
            for i, item in enumerate(history, 1):
                history_text += f"[{item['timestamp']}]\n"
                history_text += f"你: {item['user']}\n"
                history_text += f"助手: {item['assistant']}\n\n"
            return history_text
        except Exception as e:
            return f"读取历史记录失败: {str(e)}"