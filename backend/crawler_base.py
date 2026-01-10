# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from DrissionPage import ChromiumPage
import time
import json

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
    针对 DeepSeek 的定制化实现
    """
    def activate_tab(self):
        target_url = "chat.deepseek.com"
        self.tab = None

        # --- 修复逻辑：稳健获取标签页 ---
        try:
            # 尝试通过 URL 获取标签页
            # 注意：在某些版本中，如果找不到会抛出异常，而不是返回 None
            self.tab = self.page.get_tab(url=target_url)

            # 双重检查：确保获取到的对象不为空
            if self.tab:
                print(f"✅ 找到已有 DeepSeek 标签页: {self.tab.title}")
                # 将标签页置顶
                self.tab.activate()

        except Exception:
            # 如果 get_tab 抛出异常（说明没找到），这里捕获它，不让程序崩溃
            # print("当前未找到 DeepSeek 标签页，准备新建...")
            pass

        # 如果经过上面的尝试还是没有 tab，则新建
        if not self.tab:
            print("🆕 正在新建 DeepSeek 标签页...")
            self.tab = self.page.new_tab("https://chat.deepseek.com/")
            # 给页面一点加载时间，避免立即操作导致元素找不到
            time.sleep(3)

        # 再次确保页面已加载完毕
        try:
            self.tab.wait.load_start()
        except:
            pass

    def stream_chat(self, message: str):
        if not self.tab:
            self.activate_tab()

        print(f"[DeepSeek] 准备发送: {message}")

        try:
            # --- 1. 定位输入框 ---
            # 优先使用你提供的特定 Class，同时也保留 placeholder 作为兜底
            input_ele = self.tab.ele('css:textarea._27c9245')
            if not input_ele:
                input_ele = self.tab.ele('css:textarea[placeholder*="DeepSeek"]')

            if not input_ele:
                yield "[系统错误] 无法定位输入框，请检查登录状态"
                return

            # --- 2. 模拟输入 (触发 React 状态) ---
            input_ele.clear()
            # input() 方法会自动模拟点击和键盘输入，通常能触发 React 的 onChange 事件
            input_ele.input(message)

            # 关键：给 React 一点时间渲染，让发送按钮从 disable 变为 enable
            time.sleep(0.6)

            # --- 3. 点击发送按钮 ---
            # 使用你提供的 div class (包含 svg 的那个容器)
            # 这里的类名非常长，我们取其中独特的部分即可，或者用精确匹配
            send_btn = self.tab.ele('css:._7436101')
            if send_btn:
                send_btn.click()
            else:
                # 如果找不到按钮，回车通常也是有效的
                print("[DeepSeek] 未找到按钮，尝试回车发送")
                input_ele.input('\n')

            print("[DeepSeek] 消息已提交，开始监听...")

        except Exception as e:
            yield f"[系统提示] 发送指令失败: {str(e)}"
            return

        # --- 4. 开启监听 ---
        # 建议不设 targets 或设为 'completion' (取决于 URL 包含什么关键词)
        # 这里为了稳健，先监听所有，在循环里通过 JSON 结构过滤
        self.tab.listen.start('completion')

        # 变量：记录上一次已经推送给前端的字符长度
        last_text_len = 0
        start_time = time.time()

        try:
            # 设置超时 120 秒
            for packet in self.tab.listen.steps(timeout=120):
                # 过滤非 JSON 响应
                if 'application/json' not in packet.response.headers.get('content-type', ''):
                    continue

                try:
                    # 获取响应体
                    raw_data = packet.response.body

                    # --- 5. JSON 结构解析 (根据你提供的数据) ---
                    # 目标路径: data -> biz_data -> chat_messages -> [last] -> fragments -> [0] -> content
                    if not isinstance(raw_data, dict):
                        continue

                    data_node = raw_data.get("data")
                    if not data_node: continue

                    biz_data = data_node.get("biz_data")
                    if not biz_data: continue

                    chat_messages = biz_data.get("chat_messages")
                    if not chat_messages: continue

                    # 获取最新一条消息
                    latest_msg = chat_messages[-1]

                    # 必须是 AI (ASSISTANT) 的回复
                    if latest_msg.get("role") == "ASSISTANT":
                        fragments = latest_msg.get("fragments", [])
                        if fragments:
                            # 获取当前的完整文本 (DeepSeek 返回的是全量文本)
                            full_content = fragments[0].get("content", "")

                            # --- 6. 计算增量 (只发送新生成的字) ---
                            if len(full_content) > last_text_len:
                                # 截取新增加的部分
                                new_chars = full_content[last_text_len:]
                                # 更新计数器
                                last_text_len = len(full_content)
                                # Yield 出去
                                yield new_chars

                            # --- 7. 判断结束 ---
                            if latest_msg.get("status") == "FINISHED":
                                print("[DeepSeek] 生成完成")
                                break

                except Exception as parse_e:
                    # 某个包解析失败不影响整体流程
                    # print(f"解析包跳过: {parse_e}")
                    pass

                # 超时保护
                if time.time() - start_time > 120:
                    yield "\n[系统提示] 响应超时"
                    break

        finally:
            self.tab.listen.stop()

class GPTBot(BaseBot):
    def activate_tab(self): pass
    def stream_chat(self, message: str): yield ""

class BotFactory:
    @staticmethod
    def get_bot(model_name: str, page: ChromiumPage) -> BaseBot:
        if model_name == 'deepseek': return DeepSeekBot(page)
        elif model_name == 'gpt': return GPTBot(page)
        else: raise ValueError(f"Unknown model: {model_name}")