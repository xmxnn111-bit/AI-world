# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from DrissionPage import ChromiumPage
# 引入 markdownify
from markdownify import markdownify as md
import time
import asyncio
import re

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

    # === 高级工程师优化：智能内容转换层 ===
    def _safe_to_markdown(self, content: str) -> str:
        """
        智能判断内容类型并转换为 Markdown。
        策略：
        1. 如果内容为空，直接返回。
        2. 使用正则启发式检测是否包含 HTML 标签特征。
        3. 只有检测到 HTML 结构时才调用 markdownify，防止误伤纯文本（如数学公式 x < y）。
        4. 添加异常捕获，确保管道不会因为解析错误而中断。
        """
        if not content:
            return ""

        # 启发式检测：检查是否包含常见的 HTML 标签特征
        # 我们主要关注块级元素或常见的行内格式标签
        # <(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote)\b 是比较安全的特征
        html_pattern = re.compile(r'<(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote|em|strong|b|i)\b', re.IGNORECASE)

        if not html_pattern.search(content):
            # 如果没有发现明显的 HTML 标签，视为纯文本/Markdown，直接返回
            # 这样可以保护 "x < y" 这种数学公式不被当作非法 HTML 标签剔除
            print("不是纯文本")
            return content

        try:
            # heading_style="atx" 保证标题是 # 格式
            return md(content, heading_style="atx")
        except Exception as e:
            print(f"[Conversion Error] HTML转Markdown失败，降级为返回原始内容: {e}")
            return content

class DeepSeekBot(BaseBot):
    """
    针对 DeepSeek 的 DOM 流式抓取实现
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

    def stop_generation(self):
        print("[DeepSeek] 尝试停止生成...")
        if not self.tab: return
        try:
            stop_btn = self.tab.ele('css:._7436101')
            if stop_btn:
                stop_btn.click()
        except Exception as e:
            print(f"[DeepSeek] 停止操作失败: {e}")

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[DeepSeek] 准备发送: {message}")
        try:
            existing_answers = self.tab.eles('css:.ds-markdown')
            existing_count = len(existing_answers)

            input_ele = self.tab.ele('css:textarea._27c9245')
            if not input_ele: input_ele = self.tab.ele('css:textarea[placeholder*="DeepSeek"]')
            if not input_ele:
                yield "Error: 无法定位输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)
            send_btn = self.tab.ele('css:._7436101')
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[DeepSeek] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.ds-markdown')
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            yield ""
            return

        previous_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                # 获取 inner_html，因为 DrissionPage 的 inner_html 会包含标签
                # 如果是纯文本节点，它也会返回转义后的文本
                current_html = answer_box.inner_html

                if len(current_html) > previous_len:
                    # === 调用父类的安全转换方法 ===
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content

                    previous_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
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
            self.tab = self.page.get_tab(url="chatgpt.com")
            if not self.tab: self.tab = self.page.get_tab(url="openai.com")
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
        print("[GPT] 停止功能暂未配置选择器")
        pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[GPT] 准备发送: {message}")
        try:
            existing_answers = self.tab.eles('css:.markdown.markdown-new-styling')
            existing_count = len(existing_answers)
            input_ele = self.tab.ele('css:#prompt-textarea p')
            if not input_ele: input_ele = self.tab.ele('css:#prompt-textarea')
            if not input_ele:
                yield "Error: 无法定位 ChatGPT 输入框"
                return
            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)
            send_btn = self.tab.ele('css:#composer-submit-button')
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[GPT] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

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

        previous_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html
                if len(current_html) > previous_len:
                    # === 调用安全转换 ===
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[GPT] 检测到静默超时，默认生成结束")
                        break
                if time.time() - monitor_start > 60:
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
        try:
            stop_btn = self.tab.ele('css:#flow-end-msg-send')
            if stop_btn: stop_btn.click()
        except Exception:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Doubao] 准备发送: {message}")
        try:
            existing_answers = self.tab.eles('css:.container-P2rR72')
            existing_count = len(existing_answers)
            input_ele = self.tab.ele('css:.semi-input-textarea')
            if not input_ele:
                yield "Error: 无法定位豆包输入框"
                return
            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)
            send_btn = self.tab.ele('css:#flow-end-msg-send')
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[Doubao] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.container-P2rR72')
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            yield ""
            return

        previous_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html
                if len(current_html) > previous_len:
                    # === 调用安全转换 ===
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[Doubao] 检测到静默超时，默认生成结束")
                        break
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