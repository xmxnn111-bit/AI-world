# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from DrissionPage import ChromiumPage
from markdownify import markdownify as md
import time
import asyncio
import re

# 引入配置文件
from config import MODEL_CONFIG

class BaseBot(ABC):
    def __init__(self, page: ChromiumPage, model_name: str = None):
        self.page = page
        self.tab = None
        # 如果传入了 model_name，则加载对应配置
        self.conf = MODEL_CONFIG.get(model_name) if model_name else None

    @abstractmethod
    def activate_tab(self):
        pass

    @abstractmethod
    def stream_chat(self, message: str):
        pass

    def stop_generation(self):
        """
        通用的停止生成逻辑（只要配置了 stop 选择器即可工作）。
        子类如果有特殊逻辑（如 Kimi）可以重写此方法。
        """
        print(f"[{self.__class__.__name__}] 尝试停止生成...")
        if not self.tab or not self.conf: return

        try:
            stop_selector = self.conf['selectors']['stop']
            stop_btn = self._get_ele(stop_selector)

            if stop_btn:
                stop_btn.click()
                print(f"[{self.__class__.__name__}] 已点击停止按钮")
            else:
                print(f"[{self.__class__.__name__}] 未找到停止按钮")
        except Exception as e:
            print(f"[{self.__class__.__name__}] 停止操作失败: {e}")

    def _safe_to_markdown(self, content: str) -> str:
        """智能判断内容类型并转换为 Markdown"""
        if not content: return ""
        html_pattern = re.compile(r'<(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote|em|strong|b|i)\b', re.IGNORECASE)
        if not html_pattern.search(content): return content
        try:
            return md(content, heading_style="atx")
        except Exception as e:
            print(f"[Conversion Error] HTML转Markdown失败: {e}")
            return content

    def _get_ele(self, selector_config):
        """
        辅助函数：根据配置获取元素。
        支持配置为字符串（单个选择器）或列表（多个备用选择器）。
        """
        if isinstance(selector_config, list):
            for sel in selector_config:
                ele = self.tab.ele(sel)
                if ele: return ele
            return None
        else:
            return self.tab.ele(selector_config)


class DeepSeekBot(BaseBot):
    def __init__(self, page):
        super().__init__(page, 'deepseek')

    def activate_tab(self):
        target_url = self.conf['domain']
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
            self.tab = self.page.new_tab(self.conf['home_url'])
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[DeepSeek] 准备发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_answers = self.tab.eles(answer_selector)
            existing_count = len(existing_answers)

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele:
                yield "Error: 无法定位输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[DeepSeek] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles(answer_selector)
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
    def __init__(self, page):
        super().__init__(page, 'gpt')

    def activate_tab(self):
        target_url = self.conf['domain']
        alt_url = self.conf.get('alt_domain')
        self.tab = None
        try:
            self.tab = self.page.get_tab(url=target_url)
            if not self.tab and alt_url:
                self.tab = self.page.get_tab(url=alt_url)

            if self.tab:
                print(f"✅ 找到已有 ChatGPT 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass
        if not self.tab:
            print("🆕 正在新建 ChatGPT 标签页...")
            self.tab = self.page.new_tab(self.conf['home_url'])
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[GPT] 准备发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_answers = self.tab.eles(answer_selector)
            existing_count = len(existing_answers)

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele:
                yield "Error: 无法定位 ChatGPT 输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[GPT] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles(answer_selector)
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            yield ""
            return

        previous_len = 0
        monitor_start = time.time()

        # 缓冲，等待“停止”按钮出现
        time.sleep(0.5)

        while True:
            try:
                current_html = answer_box.inner_html
                if len(current_html) > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = len(current_html)
                    monitor_start = time.time()

                # --- 新增：使用停止按钮状态判断结束 ---
                # 使用 _get_ele 兼容配置可能是列表或字符串的情况
                is_generating = self._get_ele(self.conf['selectors']['stop'])

                if not is_generating:
                    # 只有当已经获取到内容后，才认为停止按钮消失代表生成结束
                    # 防止刚开始生成时按钮还没渲染出来的瞬间误判
                    if len(current_html) > 0:
                        print("[GPT] 检测到停止按钮消失，生成结束")
                        break

                # 兜底超时
                if time.time() - monitor_start > 60:
                    print("[GPT] 监听强制超时")
                    break

                await asyncio.sleep(0.1) # 稍微加快频率

            except Exception as e:
                print(f"[GPT] 监听异常: {e}")
                break

class DoubaoBot(BaseBot):
    def __init__(self, page):
        super().__init__(page, 'doubao')

    def activate_tab(self):
        target_url = self.conf['domain']
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
            self.tab = self.page.new_tab(self.conf['home_url'])
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Doubao] 准备发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_answers = self.tab.eles(answer_selector)
            existing_count = len(existing_answers)

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele:
                yield "Error: 无法定位豆包输入框"
                return
            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
            print("[Doubao] 消息已提交...")
        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles(answer_selector)
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
    def __init__(self, page):
        super().__init__(page, 'gemini')

    def activate_tab(self):
        target_url = self.conf['domain']
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
            self.tab = self.page.new_tab(self.conf['home_url'])
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Gemini] 准备发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_answers = self.tab.eles(answer_selector)
            existing_count = len(existing_answers)

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele:
                yield "Error: 无法定位 Gemini 输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')

            print("[Gemini] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles(answer_selector)
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            current_answers = self.tab.eles(answer_selector)
            if current_answers:
                answer_box = current_answers[-1]
            else:
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
                        print("[Gemini] 检测到静默超时，默认生成结束")
                        break

                if time.time() - monitor_start > 120:
                    print("[Gemini] 监听强制超时")
                    break

                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"[Gemini] 监听异常: {e}")
                break


class KimiBot(BaseBot):
    def __init__(self, page):
        super().__init__(page, 'kimi')

    def activate_tab(self):
        target_url = self.conf['domain']
        self.tab = None
        try:
            self.tab = self.page.get_tab(url=target_url)
            if self.tab:
                print(f"✅ 找到已有 Kimi 标签页: {self.tab.title}")
                self.tab.activate()
        except Exception:
            pass
        if not self.tab:
            print("🆕 正在新建 Kimi 标签页...")
            self.tab = self.page.new_tab(self.conf['home_url'])
            time.sleep(1)
        try:
            self.tab.wait.load_start()
        except:
            pass

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Kimi] 准备发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_answers = self.tab.eles(answer_selector)
            existing_count = len(existing_answers)

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele:
                yield "Error: 无法定位 Kimi 输入框"
                return

            input_ele.clear()
            input_ele.input(message)
            time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn:
                send_btn.click()
            else:
                input_ele.input('\n')
            print("[Kimi] 消息已提交...")

        except Exception as e:
            yield f"Error: 发送失败 {str(e)}"
            return

        answer_box = None
        wait_start = time.time()
        while time.time() - wait_start < 10:
            current_answers = self.tab.eles(answer_selector)
            if len(current_answers) > existing_count:
                answer_box = current_answers[-1]
                break
            time.sleep(0.2)

        if not answer_box:
            current_answers = self.tab.eles(answer_selector)
            if current_answers:
                answer_box = current_answers[-1]
            else:
                yield ""
                return

        previous_len = 0
        monitor_start = time.time()

        time.sleep(0.5)

        while True:
            try:
                current_html = answer_box.inner_html

                if len(current_html) > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = len(current_html)
                    monitor_start = time.time()

                # --- 核心修改：使用配置中的 stop 选择器检查停止状态 ---
                # 在 config.py 中，kimi 的 stop 定义为 .send-button-container.stop
                stop_selector = self.conf['selectors']['stop']
                is_generating = self.tab.ele(stop_selector)

                if not is_generating:
                    if len(current_html) > 0:
                        print("[Kimi] 检测到停止按钮类名消失，生成结束")
                        break

                if time.time() - monitor_start > 120:
                    print("[Kimi] 监听强制超时")
                    break

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"[Kimi] 监听异常: {e}")
                break


class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        elif model_name == 'doubao': return DoubaoBot(page)
        elif model_name == 'gemini': return GeminiBot(page)
        elif model_name == 'kimi': return KimiBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")