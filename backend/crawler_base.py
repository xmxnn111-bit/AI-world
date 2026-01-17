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

    @abstractmethod
    def activate_tab(self):
        pass

    @abstractmethod
    def stream_chat(self, message: str):
        pass

    def stop_generation(self):
        """通用的停止生成逻辑"""
        print(f"[{self.model_name}] 尝试停止生成...")
        if not self.tab or not self.conf: return

        try:
            stop_selector = self.conf['selectors']['stop']
            stop_btn = self._get_ele(stop_selector)

            if stop_btn:
                stop_btn.click()
                print(f"[{self.model_name}] 已点击停止按钮")
            else:
                print(f"[{self.model_name}] 未找到停止按钮")
        except Exception as e:
            print(f"[{self.model_name}] 停止操作失败: {e}")

    def _safe_to_markdown(self, content: str) -> str:
        """智能判断内容类型并转换为 Markdown"""
        if not content: return ""
        html_pattern = re.compile(r'<(p|div|span|pre|code|br|ul|ol|li|h[1-6]|table|blockquote|em|strong|b|i)\b', re.IGNORECASE)
        if not html_pattern.search(content): return content
        try:
            return md(content, heading_style="atx")
        except Exception:
            return content

    def _get_ele(self, selector_config):
        """辅助函数：根据配置获取元素"""
        if isinstance(selector_config, list):
            for sel in selector_config:
                ele = self.tab.ele(sel)
                if ele: return ele
            return None
        else:
            return self.tab.ele(selector_config)

    def _wait_for_answer_box(self, existing_count, timeout=10):
        """等待新回答框出现的通用逻辑"""
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
        """
        核心优化：稳健的流式监听循环
        包含：元素保活、双重防抖退出、超时保护
        """
        previous_len = 0

        # 初始缓冲，等待 UI 稳定 (新聊天尤其重要)
        time.sleep(2)

        # 计时器初始化
        last_content_change_time = time.time()
        stop_btn_missing_start_time = None # 记录停止按钮开始消失的时间点

        while True:
            try:
                # [关键优化] 元素保活：如果 2秒 没动静，尝试重新获取最新的 answer_box
                # 解决页面局部重绘导致持有的 element 失效的问题
                if time.time() - last_content_change_time > 2:
                    try:
                        latest_answers = self.tab.eles(answer_selector)
                        if latest_answers:
                            answer_box = latest_answers[-1]
                    except:
                        pass # 忽略刷新失败

                # 获取内容
                current_html = answer_box.inner_html
                current_len = len(current_html)

                # --- 状态检查 1：内容变化 ---
                if current_len > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content
                    previous_len = current_len
                    last_content_change_time = time.time() # 重置内容静默计时
                    stop_btn_missing_start_time = None # 内容在变，说明还在生成

                # --- 状态检查 2：停止按钮 ---
                is_generating = self._get_ele(self.conf['selectors']['stop'])

                if not is_generating:
                    if stop_btn_missing_start_time is None:
                        stop_btn_missing_start_time = time.time()
                else:
                    stop_btn_missing_start_time = None # 按钮出现了，重置消失计时

                # --- 计算持续时间 ---
                content_silence_duration = time.time() - last_content_change_time

                btn_missing_duration = 0
                if stop_btn_missing_start_time:
                    btn_missing_duration = time.time() - stop_btn_missing_start_time

                # --- 退出判定 (双重防抖) ---
                # 条件：内容 3秒没变 AND 停止按钮 持续消失超过 2秒
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

class DeepSeekBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'deepseek')

    def activate_tab(self):
        try:
            # 1. 尝试按域名查找
            self.tab = self.page.get_tab(url=self.conf['domain'])
            if self.tab:
                print(f"✅ [DeepSeek] 找到已有标签页: {self.tab.title}")
                self.tab.activate()
                return # 成功找到并激活，直接返回
        except Exception as e:
            print(f"⚠️ [DeepSeek] 查找标签页时出错: {e}")

        # 2. 如果没找到，新建
        print("🆕 [DeepSeek] 未找到已有页面，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(1)

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

        async for chunk in self._robust_stream_loop(answer_box, answer_selector):
            yield chunk

class GPTBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'gpt')

    def activate_tab(self):
        try:
            # GPT 检查两个域名
            self.tab = self.page.get_tab(url=self.conf['domain'])
            if not self.tab and self.conf.get('alt_domain'):
                self.tab = self.page.get_tab(url=self.conf['alt_domain'])

            if self.tab:
                print(f"✅ [GPT] 找到已有标签页: {self.tab.title}")
                self.tab.activate()
                return
        except Exception as e:
            print(f"⚠️ [GPT] 查找标签页时出错: {e}")

        print("🆕 [GPT] 未找到已有页面，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(1)

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

        async for chunk in self._robust_stream_loop(answer_box, answer_selector):
            yield chunk

class DoubaoBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'doubao')

    def activate_tab(self):
        try:
            self.tab = self.page.get_tab(url=self.conf['domain'])
            if self.tab:
                print(f"✅ [Doubao] 找到已有标签页: {self.tab.title}")
                self.tab.activate()
                return
        except Exception as e:
            print(f"⚠️ [Doubao] 查找标签页时出错: {e}")

        print("🆕 [Doubao] 未找到已有页面，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(1)

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

        async for chunk in self._robust_stream_loop(answer_box, answer_selector):
            yield chunk

class GeminiBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'gemini')

    def activate_tab(self):
        try:
            self.tab = self.page.get_tab(url=self.conf['domain'])
            if self.tab:
                print(f"✅ [Gemini] 找到已有标签页: {self.tab.title}")
                self.tab.activate()
                return
        except Exception as e:
            print(f"⚠️ [Gemini] 查找标签页时出错: {e}")

        print("🆕 [Gemini] 未找到已有页面，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(1)

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

        async for chunk in self._robust_stream_loop(answer_box, answer_selector):
            yield chunk

class KimiBot(BaseBot):
    def __init__(self, page): super().__init__(page, 'kimi')

    def activate_tab(self):
        try:
            self.tab = self.page.get_tab(url=self.conf['domain'])
            if self.tab:
                print(f"✅ [Kimi] 找到已有标签页: {self.tab.title}")
                self.tab.activate()
                return
        except Exception as e:
            print(f"⚠️ [Kimi] 查找标签页时出错: {e}")

        print("🆕 [Kimi] 未找到已有页面，正在新建...")
        self.tab = self.page.new_tab(self.conf['home_url'])
        time.sleep(1)

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

        async for chunk in self._robust_stream_loop(answer_box, answer_selector):
            yield chunk

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        elif model_name == 'doubao': return DoubaoBot(page)
        elif model_name == 'gemini': return GeminiBot(page)
        elif model_name == 'kimi': return KimiBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")