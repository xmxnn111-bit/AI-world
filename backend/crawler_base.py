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

    def _safe_to_markdown(self, content: str) -> str:
        """
        智能判断内容类型并转换为 Markdown。
        """
        if not content:
            return ""

        # 启发式检测：检查是否包含常见的 HTML 标签特征
        html_pattern = re.compile(r'<(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote|em|strong|b|i)\b', re.IGNORECASE)

        if not html_pattern.search(content):
            return content

        try:
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
                print("[DeepSeek] 已点击停止按钮")
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
                current_html = answer_box.inner_html

                if len(current_html) > previous_len:
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
        print("[GPT] 尝试停止生成...")
        if not self.tab: return

        try:
            stop_btn = self.tab.ele('css:#composer-submit-button')

            if stop_btn:
                stop_btn.click()
                print("[GPT] 已点击停止按钮 (#composer-submit-button)")
            else:
                stop_btn = self.tab.ele('css:[data-testid="stop-button"]')
                if stop_btn:
                    stop_btn.click()
                    print("[GPT] 已点击停止按钮 (fallback)")
                else:
                    print("[GPT] 未找到停止按钮 (可能已完成生成)")
        except Exception as e:
            print(f"[GPT] 停止操作异常: {e}")

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
            if not send_btn: send_btn = self.tab.ele('css:[data-testid="send-button"]')

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

class GeminiBot(BaseBot):
    """
    针对 Gemini 的 DOM 流式抓取实现
    """
    def activate_tab(self):
        target_url = "gemini.google.com"
        self.tab = None
        try:
            self.tab = self.page.get_tab(url=target_url)
            if self.tab:
                print(f"✅ 找到已有 Gemini 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass
        if not self.tab:
            print("🆕 正在新建 Gemini 标签页...")
            self.tab = self.page.new_tab("https://gemini.google.com/")
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    def stop_generation(self):
        print("[Gemini] 尝试停止生成...")
        if not self.tab: return
        try:
            # 用户指定的停止按钮选择器
            stop_btn = self.tab.ele('css:button[aria-label="停止回答"]')
            if stop_btn:
                stop_btn.click()
                print("[Gemini] 已点击停止按钮")
        except Exception as e:
            print(f"[Gemini] 停止操作失败: {e}")

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Gemini] 准备发送: {message}")
        try:
            # 1. 记录当前回答数量
            # 用户指定的输出内容选择器
            existing_answers = self.tab.eles('css:.markdown.markdown-main-panel')
            existing_count = len(existing_answers)

            # 2. 定位输入框
            # 用户指定的输入框选择器
            input_ele = self.tab.ele('css:.ql-editor.textarea p')
            if not input_ele:
                # 兜底：如果 p 标签不存在，尝试直接找 editor
                input_ele = self.tab.ele('css:.ql-editor.textarea')

            if not input_ele:
                yield "Error: 无法定位 Gemini 输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            # 3. 点击发送
            # 用户指定的发送按钮选择器
            send_btn = self.tab.ele('css:.send-button')
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')

            print("[Gemini] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        # 4. 等待新回答出现
        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles('css:.markdown.markdown-main-panel')
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            # 如果没找到新增的，可能是第一次或者是新开的会话，尝试拿最后一个
            current_answers = self.tab.eles('css:.markdown.markdown-main-panel')
            if current_answers:
                answer_box = current_answers[-1]
            else:
                yield ""
                return

        # 5. 流式输出
        previous_len = 0
        monitor_start = time.time()
        last_change_time = time.time()

        while True:
            try:
                current_html = answer_box.inner_html

                if len(current_html) > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content

                    previous_len = len(current_html)
                    last_change_time = time.time()
                    monitor_start = time.time()
                else:
                    # 如果内容不再变化且已有内容，默认生成结束
                    if time.time() - last_change_time > 3 and len(current_html) > 0:
                        print("[Gemini] 检测到静默超时，默认生成结束")
                        break

                # 强制超时保护
                if time.time() - monitor_start > 120:
                    print("[Gemini] 监听强制超时")
                    break

                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"[Gemini] 监听异常: {e}")
                break

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        elif model_name == 'doubao': return DoubaoBot(page)
        elif model_name == 'gemini': return GeminiBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")