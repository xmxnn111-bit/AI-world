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
        self.conf = MODEL_CONFIG.get(model_name) if model_name else None
        self.model_name = model_name

    def activate_tab(self):
        """
        激活或新建标签页 (回归原生 get_tab 方法)
        """
        # 1. 尝试使用 domain 查找 (DrissionPage 会自动进行模糊匹配)
        if self.conf.get('domain'):
            try:
                self.tab = self.page.get_tab(url=self.conf['domain'])
            except Exception:
                self.tab = None

        # 2. 如果没找到，尝试 alt_domain
        if not self.tab and self.conf.get('alt_domain'):
            try:
                self.tab = self.page.get_tab(url=self.conf['alt_domain'])
            except Exception:
                self.tab = None

        # 3. 找到则激活
        if self.tab:
            print(f"✅ [{self.model_name}] 复用标签页: {self.tab.title}")
            return

        # 4. 没找到则新建
        print(f"🆕 [{self.model_name}] 未找到页面 (匹配规则: {self.conf.get('domain')})，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(2)

    @abstractmethod
    def stream_chat(self, message: str):
        pass

    def stop_generation(self):
        """停止生成逻辑"""
        print(f"[{self.model_name}] 尝试停止生成...")
        if not self.tab or not self.conf: return

        try:
            stop_selector = self.conf['selectors']['stop']
            stop_btn = self._get_ele(stop_selector)

            if stop_btn:
                stop_btn.click()
                print(f"[{self.model_name}] 已点击停止按钮")
            else:
                print(f"[{self.model_name}] 未找到停止按钮 (可能已结束)")
        except Exception as e:
            print(f"[{self.model_name}] 停止操作失败: {e}")

    def _safe_to_markdown(self, content: str) -> str:
        if not content: return ""
        html_pattern = re.compile(r'<(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote|em|strong|b|i)\b', re.IGNORECASE)
        if not html_pattern.search(content): return content
        try:
            return md(content, heading_style="atx")
        except Exception:
            return content

    def _get_ele(self, selector_config):
        if not self.tab: return None
        if isinstance(selector_config, list):
            for sel in selector_config:
                ele = self.tab.ele(sel)
                if ele: return ele
            return None
        else:
            return self.tab.ele(selector_config)

    def _wait_for_answer_box(self, existing_count, timeout=10):
        answer_selector = self.conf['selectors']['answer']
        wait_start = time.time()
        while time.time() - wait_start < timeout:
            current_answers = self.tab.eles(answer_selector)
            if len(current_answers) > existing_count:
                return current_answers[-1]
            time.sleep(0.2)

        current_answers = self.tab.eles(answer_selector)
        if current_answers:
            return current_answers[-1]
        return None

    async def _robust_stream_loop(self, answer_box, answer_selector):
        """流式监听循环"""
        previous_len = 0
        time.sleep(2)
        last_content_change_time = time.time()
        stop_btn_missing_start_time = None

        while True:
            try:
                # 元素保活 (防止页面重绘导致元素失效)
                if time.time() - last_content_change_time > 2:
                    try:
                        latest_answers = self.tab.eles(answer_selector)
                        if latest_answers:
                            answer_box = latest_answers[-1]
                    except:
                        pass

                # 获取内容
                current_html = answer_box.inner_html
                current_len = len(current_html)

                # --- 状态检查 1：内容变化 ---
                if current_len > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = current_len
                    last_content_change_time = time.time()
                    stop_btn_missing_start_time = None

                # --- 状态检查 2：停止按钮 ---
                # 使用配置中的 stop 选择器 (含 aria-disabled 检查)
                is_generating = self._get_ele(self.conf['selectors']['stop'])

                if not is_generating:
                    if stop_btn_missing_start_time is None:
                        stop_btn_missing_start_time = time.time()
                else:
                    stop_btn_missing_start_time = None

                # --- 计算持续时间 ---
                content_silence_duration = time.time() - last_content_change_time
                btn_missing_duration = 0
                if stop_btn_missing_start_time:
                    btn_missing_duration = time.time() - stop_btn_missing_start_time

                # --- 退出判定 (双重防抖) ---
                if content_silence_duration > 3 and btn_missing_duration > 2:
                    print(f"[{self.model_name}] 生成结束 (静默+按钮消失确认)")
                    break

                # --- 超时保护 ---
                if content_silence_duration > 60:
                    print(f"[{self.model_name}] 超时退出 (60s无响应)")
                    break

                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"监听异常: {e}")
                break

# --- Bot 实现 (复用 BaseBot 逻辑) ---

class DeepSeekBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'deepseek')

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[DeepSeek] 发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_count = len(self.tab.eles(answer_selector))

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele: yield "Error: 找不到输入框"; return

            input_ele.clear(); input_ele.input(message); time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
        except Exception as e: yield f"Error: {e}"; return

        answer_box = self._wait_for_answer_box(existing_count)
        if not answer_box: yield ""; return
        async for chunk in self._robust_stream_loop(answer_box, answer_selector): yield chunk

class GPTBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'gpt')

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[GPT] 发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_count = len(self.tab.eles(answer_selector))

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele: yield "Error: 找不到输入框"; return
            input_ele.clear(); input_ele.input(message); time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
        except Exception as e: yield f"Error: {e}"; return

        answer_box = self._wait_for_answer_box(existing_count)
        if not answer_box: yield ""; return
        async for chunk in self._robust_stream_loop(answer_box, answer_selector): yield chunk

class DoubaoBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'doubao')

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Doubao] 发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_count = len(self.tab.eles(answer_selector))

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele: yield "Error: 找不到输入框"; return
            input_ele.clear(); input_ele.input(message); time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
        except Exception as e: yield f"Error: {e}"; return

        answer_box = self._wait_for_answer_box(existing_count)
        if not answer_box: yield ""; return
        async for chunk in self._robust_stream_loop(answer_box, answer_selector): yield chunk

class GeminiBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'gemini')

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Gemini] 发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_count = len(self.tab.eles(answer_selector))

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele: yield "Error: 找不到输入框"; return
            input_ele.clear(); input_ele.input(message); time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
        except Exception as e: yield f"Error: {e}"; return

        answer_box = self._wait_for_answer_box(existing_count)
        if not answer_box: yield ""; return
        async for chunk in self._robust_stream_loop(answer_box, answer_selector): yield chunk

class KimiBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'kimi')

    async def stream_chat(self, message: str):
        if not self.tab: self.activate_tab()
        print(f"[Kimi] 发送: {message}")
        try:
            answer_selector = self.conf['selectors']['answer']
            existing_count = len(self.tab.eles(answer_selector))

            input_ele = self._get_ele(self.conf['selectors']['input'])
            if not input_ele: yield "Error: 找不到输入框"; return
            input_ele.clear(); input_ele.input(message); time.sleep(0.5)

            send_btn = self._get_ele(self.conf['selectors']['send'])
            if send_btn: send_btn.click()
            else: input_ele.input('\n')
        except Exception as e: yield f"Error: {e}"; return

        answer_box = self._wait_for_answer_box(existing_count)
        if not answer_box: yield ""; return
        async for chunk in self._robust_stream_loop(answer_box, answer_selector): yield chunk

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        elif model_name == 'doubao': return DoubaoBot(page)
        elif model_name == 'gemini': return GeminiBot(page)
        elif model_name == 'kimi': return KimiBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")