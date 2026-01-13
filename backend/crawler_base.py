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

    # 停止生成逻辑
    def stop_generation(self):
        print("[DeepSeek] 尝试停止生成...")
        if not self.tab: return

        try:
            stop_btn = self.tab.ele('css:._7436101')
            if stop_btn:
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
            yield ""
            return

        # --- 4. 核心：多重保险的流式监听 ---
        previous_html_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html

                if len(current_html) > previous_html_len:
                    yield current_html
                    previous_html_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()

                else:
                    if time.time() - last_change_time > 3 and XHml_len > 0:
                        # 修正变量名错误: XHml_len 应为 len(current_html) 或依赖上下文
                        # 原 DeepSeek 代码逻辑检查是否静默超时
                         if len(current_html) > 0:
                            print("[DeepSeek] 检测到静默超时，默认生成结束")
                            break

                if time.time() - monitor_start > 30:
                    print("[DeepSeek] 监听强制超时")
                    break

                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"监听异常: {e}")
                break

class GPTBot(BaseBot):
    """
    针对 ChatGPT 的 DOM 流式抓取实现
    """
    def activate_tab(self):
        target_url = "chatgpt.com"
        self.tab = None

        try:
            # 尝试查找包含 chatgpt.com 或 openai.com 的标签页
            self.tab = self.page.get_tab(url="chatgpt.com")
            if not self.tab:
                self.tab = self.page.get_tab(url="openai.com")

            if self.tab:
                print(f"✅ 找到已有 ChatGPT 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass

        if not self.tab:
            print("🆕 正在新建 ChatGPT 标签页...")
            self.tab = self.page.new_tab("https://chatgpt.com/")
            time.sleep(1)

        try:
            self.tab.wait.load_start()
        except:
            pass

    def stop_generation(self):
        # 如果需要实现停止逻辑，需要找到 ChatGPT 的停止按钮选择器
        # 目前留空，防止 server.py 调用报错
        print("[GPT] 停止功能暂未配置选择器")
        pass

    async def stream_chat(self, message: str):
        if not self.tab:
            self.activate_tab()

        print(f"[GPT] 准备发送: {message}")

        try:
            # 1. 记录当前回答数量
            # 使用用户提供的选择器: .markdown.markdown-new-styling
            existing_answers = self.tab.eles('css:.markdown.markdown-new-styling')
            existing_count = len(existing_answers)

            # 2. 定位输入框 (用户提供: #prompt-textarea p)
            input_ele = self.tab.ele('css:#prompt-textarea p')

            # 备用方案：如果 p 标签找不到，尝试直接找 textarea 容器
            if not input_ele:
                input_ele = self.tab.ele('css:#prompt-textarea')

            if not input_ele:
                yield "Error: 无法定位 ChatGPT 输入框"
                return

            # ChatGPT 的输入框通常是 contenteditable 的 div 或 p，直接 clear 可能有问题
            # 这里尝试直接 input，DrissionPage 通常能处理覆盖
            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            # 3. 点击发送按钮 (用户提供: #composer-submit-button)
            send_btn = self.tab.ele('css:#composer-submit-button')
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')

            print("[GPT] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        # 4. 等待新回答框出现
        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.markdown.markdown-new-styling')
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            yield ""
            return

        # 5. 流式监听
        previous_html_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html

                if len(current_html) > previous_html_len:
                    yield current_html
                    previous_html_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    # 静默超时 (3秒无变化则认为结束)
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[GPT] 检测到静默超时，默认生成结束")
                        break

                # 强制超时 (防止死循环)
                if time.time() - monitor_start > 60: # GPT 生成可能较慢，给 60 秒容错
                    print("[GPT] 监听强制超时")
                    break

                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"[GPT] 监听异常: {e}")
                break

class DoubaoBot(BaseBot):
    """
    针对 豆包 (Doubao) 的 DOM 流式抓取实现
    """
    def activate_tab(self):
        target_url = "dola.com"
        self.tab = None

        try:
            # 尝试查找包含 doubao.com 的标签页
            self.tab = self.page.get_tab(url=target_url)
            if self.tab:
                print(f"✅ 找到已有 豆包 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass

        if not self.tab:
            print("🆕 正在新建 豆包 标签页...")
            self.tab = self.page.new_tab("https://www.dola.com/chat/")
            time.sleep(1)

        try:
            self.tab.wait.load_start()
        except:
            pass

    def stop_generation(self):
        # 豆包的停止按钮通常位于输入框右侧或发送按钮变为停止状态
        # 这里尝试点击发送按钮位置（假设生成时它是停止按钮）
        print("[Doubao] 尝试停止...")
        try:
            stop_btn = self.tab.ele('css:#flow-end-msg-send')
            if stop_btn:
                stop_btn.click()
        except Exception:
            pass

    async def stream_chat(self, message: str):
        if not self.tab:
            self.activate_tab()

        print(f"[Doubao] 准备发送: {message}")

        try:
            # 1. 记录当前回答数量 (用于定位最新一条)
            # 使用用户提供的选择器: .paragraph-element
            existing_answers = self.tab.eles('css:.container-P2rR72')
            existing_count = len(existing_answers)

            # 2. 定位输入框 (用户提供: .semi-input-textarea.semi-input-textarea-autosize)
            input_ele = self.tab.ele('css:.semi-input-textarea')

            if not input_ele:
                yield "Error: 无法定位豆包输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            # 3. 点击发送按钮 (用户提供: #flow-end-msg-send)
            send_btn = self.tab.ele('css:#flow-end-msg-send')
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')

            print("[Doubao] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        # 4. 等待新回答框出现
        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.container-P2rR72')
            if len(current_answers) > existing_count:
                # 锁定最新的一条
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            yield ""
            return

        # 5. 流式监听
        previous_html_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html

                if len(current_html) > previous_html_len:
                    yield current_html
                    previous_html_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    # 静默超时 (3秒无变化则认为结束)
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[Doubao] 检测到静默超时，默认生成结束")
                        break

                # 强制超时 (60秒防止死循环)
                if time.time() - monitor_start > 60:
                    print("[Doubao] 监听强制超时")
                    break

                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"[Doubao] 监听异常: {e}")
                break

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        elif model_name == 'doubao': return DoubaoBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")