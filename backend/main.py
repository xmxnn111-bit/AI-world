import uvicorn
import asyncio
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 如果尚未安装 DrissionPage，请先安装: pip install drissionpage
# from DrissionPage import ChromiumPage, ChromiumOptions

# 配置简单的日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIModelHandler:
    """
    业务逻辑层：负责管理浏览器实例及处理 AI 对话逻辑。
    目前处于 Mock 模式，用于调试前端 WebSocket 连接和流式渲染。
    """

    _instance = None

    def __new__(cls):
        """实现单例模式，确保全局只有一个浏览器控制实例"""
        if cls._instance is None:
            cls._instance = super(AIModelHandler, cls).__new__(cls)
            cls._instance.browser = None
        return cls._instance

    def initialize_browser(self):
        """
        初始化 DrissionPage 浏览器对象。
        在真实环境中，这里会启动 Chromium 浏览器。
        """
        logger.info("正在初始化浏览器服务 (Mock Mode)...")
        # TODO: 【真实逻辑替换区域】
        # co = ChromiumOptions().auto_port()
        # self.browser = ChromiumPage(addr_or_opts=co)
        # logger.info("DrissionPage 浏览器已启动。")
        pass

    async def chat_stream(self, model: str, message: str) -> AsyncGenerator[str, None]:
        """
        核心生成器函数：模拟 AI 流式回复。

        Args:
            model (str): 前端传递的模型标识 (e.g., "gpt", "deepseek")
            message (str): 用户输入的 prompt

        Yields:
            str: 每次生成的文本片段
        """
        logger.info(f"收到生成请求 -> 模型: [{model}] | 消息: [{message}]")

        # 1. 模拟网络延迟和 AI "思考" 时间
        await asyncio.sleep(1)

        # 2. 定义模拟回复文本 (包含 Markdown 格式以便测试前端渲染)
        mock_response = (
            f"**[Mock模式: {model}]**\n\n"
            f"收到你的消息：*{message}*\n\n"
            f"这是一个模拟的流式回复。后端并没有真正调用浏览器，而是通过 `asyncio` 模拟了打字机效果。\n"
            f"在真实开发阶段，这里将被替换为 DrissionPage 的监听逻辑：\n"
            f"```python\n"
            f"# TODO: 监听浏览器数据包\n"
            f"for packet in tab.listen.steps():\n"
            f"    yield packet.text\n"
            f"```\n"
            f"祝你前端 React 对接顺利！🚀"
        )

        # 3. 模拟打字机流式输出 (每隔 0.05秒 推送一个字符)
        # TODO: 【真实逻辑替换区域】此处未来将替换为 DrissionPage 抓取到的实时文本流
        for char in mock_response:
            yield char
            # 随机一点微小的延迟波动，让效果更逼真
            await asyncio.sleep(0.02)

# --- FastAPI App 设置 ---

app = FastAPI(title="AI Nexus Backend", version="1.0.0")

# 配置跨域资源共享 (CORS)
# 允许 React 开发服务器 (通常是 localhost:5173) 访问，或允许所有 "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化业务处理器单例
ai_handler = AIModelHandler()

@app.on_event("startup")
async def startup_event():
    """服务启动时初始化资源"""
    ai_handler.initialize_browser()

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时清理资源"""
    if ai_handler.browser:
        # ai_handler.browser.quit() # 关闭浏览器
        logger.info("浏览器资源已释放。")

# --- WebSocket 路由 ---

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    处理 /ws/chat 的 WebSocket 连接
    """
    await websocket.accept()
    logger.info("前端 WebSocket 已连接")

    try:
        while True:
            # 1. 接收前端 JSON 数据
            # 格式: {"model": "gpt", "message": "hello"}
            data = await websocket.receive_json()

            user_model = data.get("model", "unknown")
            user_message = data.get("message", "")

            if not user_message:
                continue

            # 2. 调用业务逻辑层，获取流式生成器
            stream_generator = ai_handler.chat_stream(user_model, user_message)

            # 3. 迭代生成器，实时推送数据给前端
            async for text_chunk in stream_generator:
                # 直接发送文本片段
                await websocket.send_text(text_chunk)

            # 4. 结束标志：发送特定字符串告诉前端本次生成结束
            # 前端收到此标记后，应停止加载动画并启用输入框
            await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        logger.warning("前端断开连接 (WebSocketDisconnect)")
    except Exception as e:
        logger.error(f"WebSocket 内部错误: {str(e)}")
        # 发生错误时也可以尝试发送一个错误提示给前端，防止前端一直 loading
        try:
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.send_text("[DONE]")
        except:
            pass

if __name__ == "__main__":
    # 启动开发服务器
    # 访问地址: ws://127.0.0.1:8000/ws/chat
    print("正在启动 AI Nexus 后端服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)