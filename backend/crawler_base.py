# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from DrissionPage import ChromiumPage
import time
import asyncio

class BaseBot(ABC):
    def __init__(self, page: ChromiumPage):
        self.page = page
        self.tab = None

    @abstractmethod
    def activate_tab(self):
        pass

    @abstractmethod
    def stream_chat(self, message: str):
        pass

class DeepSeekBot(BaseBot):
    """
    针对 DeepSeek 的 DOM 流式抓取实现 (HTML版本)
    """
    def activate_tab(self):
        target_url = "chat.deepseek.com"
        self.tab = None

        try:
            self.tab = self.page.get_tab(url=target_url)
            if self.tab:
                print(f"✅ 找到已有 DeepSeek 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass

        if not self.tab:
            print("🆕 正在新建 DeepSeek 标签页...")
            self.tab = self.page.new_tab("https://chat.deepseek.com/")
            time.sleep(1)

        try:
            self.tab.wait.load_start()
        except:
            pass

# 新增：停止生成逻辑
    def stop_generation(self):
        print("[DeepSeek] 尝试停止生成...")
        if not self.tab: return

        # 定位按钮：发送按钮和停止按钮通常是同一个 DOM 元素
        # 停止按钮状态：没有 .ds-icon-button--disabled 类，aria-disabled="false"
        try:
            stop_btn = self.tab.ele('css:._7436101')
            if stop_btn:
                # 我们可以检查一下状态，或者直接点击（因为前端只在生成时才允许点停止）
                # 如果你想严谨一点，可以检查 class
                # class_attr = stop_btn.attr('class')
                # if 'ds-icon-button--disabled' not in class_attr:
                stop_btn.click()
                print("[DeepSeek] 已点击停止按钮")
        except Exception as e:
            print(f"[DeepSeek] 停止操作失败: {e}")

    async def stream_chat(self, message: str):
        if not self.tab:
            self.activate_tab()

        print(f"[DeepSeek] 准备发送: {message}")

        try:
            # 1. 记录当前回答数量 (用于定位最新一条)
            existing_answers = self.tab.eles('css:.ds-markdown')
            existing_count = len(existing_answers)

            # 2. 定位输入框并发送
            input_ele = self.tab.ele('css:textarea._27c9245')
            if not input_ele:
                input_ele = self.tab.ele('css:textarea[placeholder*="DeepSeek"]')

            if not input_ele:
                yield "Error: 无法定位输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            # 点击发送
            send_btn = self.tab.ele('css:._7436101')
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')

            print("[DeepSeek] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        # 3. 等待新回答框出现 (最多等 10 秒)
        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.ds-markdown')
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1] # 锁定最新的一条
                break
            time.sleep(0.2)

        if not answer_box:
            yield "" # 没等到新框，可能网络卡了，直接结束本次对话
            return

        # --- 4. 核心：多重保险的流式监听 ---
        previous_html_len = 0
        monitor_start = time.time()
        last_change_time = time.time() # 上次内容变化的时间

        while True:
            try:
                # 实时获取 HTML
                current_html = answer_box.inner_html

                # A. 内容有更新
                if len(current_html) > previous_html_len:
                    yield current_html # 全量发送
                    previous_html_len = len(current_html)
                    last_change_time = time.time() # 更新活跃时间
                    monitor_start = time.time()    # 重置总超时

                # B. 内容无更新 -> 检查是否该退出了
                else:
                    # 1. 静默超时检测 (最稳健的退出机制)
                    # 如果超过 3 秒内容没变，且内容不为空，认为生成结束
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[DeepSeek] 检测到静默超时，默认生成结束")
                        break

                    # 3. 发送按钮检测
                    # DeepSeek 生成时发送按钮通常是“停止(Stop)”图标，生成完变回“发送(Send)”
                    # 如果能再次找到发送按钮，说明已就绪
                    # (这里复用上面的 send_btn 选择器逻辑，或者根据实际情况调整)
                    # if self.tab.ele('css:._7436101', timeout=0.1):
                    #    pass

                # C. 总超时保护 (防止死循环)
                if time.time() - monitor_start > 30:
                    print("[DeepSeek] 监听强制超时")
                    break

                # 关键：使用 asyncio.sleep 允许 server.py 接收停止信号
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"监听异常: {e}")
                break

class GPTBot(BaseBot):
    def activate_tab(self): pass
    def stream_chat(self, message: str): yield "GPT 暂未实现"

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")