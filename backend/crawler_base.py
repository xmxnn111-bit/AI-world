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
        激活或新建标签页 (智能等待版)
        """
        # 1. 尝试使用 domain 查找
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
        print(f"🆕 [{self.model_name}] 新建页面: {self.conf['home_url']}")
        self.tab = self.page.new_tab(self.conf['home_url'])

        # 优化：等待输入框出现，最多等 10 秒
        try:
            if 'selectors' in self.conf and 'input' in self.conf['selectors']:
                self.tab.wait.ele(self.conf['selectors']['input'], timeout=10)
        except:
            pass

    @abstractmethod
    async def stream_chat(self, message: str):
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
        """HTML 转 Markdown (H1-H6 修复版)"""
        if not content: return ""
        try:
            # heading_style="atx" 确保生成 # Title 格式
            md_content = md(
                content,
                heading_style="atx",
                strip=['script', 'style']
            )
            return md_content.strip()
        except Exception as e:
            print(f"Markdown转换失败: {e}")
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
        """
        流式监听循环 (极速响应 + 强制兜底版)
        """
        previous_len = 0
        await asyncio.sleep(0.5)

        last_content_change_time = time.time()
        stop_btn_missing_start_time = None

        while True:
            try:
                # --- 1. 元素保活 ---
                try:
                    _ = answer_box.tag
                except:
                    latest_answers = self.tab.eles(answer_selector)
                    if latest_answers:
                        answer_box = latest_answers[-1]

                # --- 2. 获取内容 ---
                current_html = answer_box.inner_html
                current_len = len(current_html)

                # --- 3. 状态检查：内容变化 ---
                if current_len > previous_len:
                    markdown_content = self._safe_to_markdown(current_html)
                    yield markdown_content

                    previous_len = current_len
                    last_content_change_time = time.time()
                    stop_btn_missing_start_time = None

                # --- 4. 状态检查：停止按钮 ---
                is_generating = self._get_ele(self.conf['selectors']['stop'])

                if not is_generating:
                    if stop_btn_missing_start_time is None:
                        stop_btn_missing_start_time = time.time()
                else:
                    stop_btn_missing_start_time = None

                # --- 5. 计算持续时间 ---
                now = time.time()
                content_silence_duration = now - last_content_change_time
                btn_missing_duration = 0
                if stop_btn_missing_start_time:
                    btn_missing_duration = now - stop_btn_missing_start_time

                # --- 6. 退出判定策略 (组合策略) ---
                should_break = False

                # 策略 A: 按钮消失 + 短暂静默 (最常见：生成完毕)
                if btn_missing_duration > 0.5 and content_silence_duration > 0.8:
                    should_break = True

                # 策略 B: 按钮还在 + 长时间静默 (异常：可能卡死)
                elif content_silence_duration > 5:
                    should_break = True

                # 策略 C: 绝对超时 (防止死循环)
                elif content_silence_duration > 60:
                    should_break = True

                if should_break:
                    # === 核心修改：只要决定退出，就强制抓取最后一次 ===
                    print(f"[{self.model_name}] 🛑 抓取结束条件触发，执行最终兜底...")
                    try:
                        # 不管长度有没有变，最后再发一次，确保万无一失
                        final_content = self._safe_to_markdown(answer_box.inner_html)
                        yield final_content
                    except Exception as e:
                        # 如果此时元素正好被销毁了，那也没办法，忽略即可
                        pass
                    break

                # 极短间隔，保证响应速度
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"监听异常: {e}")
                break

# --- Bot 实现 ---

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