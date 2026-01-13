import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from crawler_base import BotFactory, ChromiumPage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化浏览器
try:
    page = ChromiumPage()
    print("浏览器后端初始化成功")
except Exception as e:
    print(f"浏览器启动失败: {e}")
    page = None

# 全局变量：记录当前正在进行的聊天任务
current_chat_task = None
current_bot = None

async def handle_chat_stream(websocket: WebSocket, bot, message: str):
    """独立的聊天任务协程"""
    try:
        # stream_chat 现在是异步生成器，使用 async for
        async for content in bot.stream_chat(message):
            await websocket.send_text(content)

        await websocket.send_text("[DONE]")

    except asyncio.CancelledError:
        print("任务被取消 (Stop)")
        await websocket.send_text("[DONE]")
    except Exception as e:
        print(f"流式传输错误: {e}")
        await websocket.send_text(f"[Error]: {str(e)}")
        await websocket.send_text("[DONE]")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global current_chat_task, current_bot

    if not page:
        await websocket.send_text("Error: 后端浏览器未启动")
        await websocket.close()
        return

    try:
        while True:
            # 主循环：时刻等待前端指令
            data = await websocket.receive_json()

            # 判断指令类型
            msg_type = data.get("type", "chat") # 默认为 chat

            # === 情况 A: 停止生成 ===
            if msg_type == "stop":
                print("收到停止指令")
                # 1. 取消当前的 Python 监听任务
                if current_chat_task and not current_chat_task.done():
                    current_chat_task.cancel()

                # 2. 调用爬虫去点击网页上的停止按钮
                if current_bot:
                    current_bot.stop_generation()
                continue

            # === 情况 B: 开始新对话 ===
            model_name = data.get("model")
            user_msg = data.get("message")

            if not model_name or not user_msg:
                continue

            # 如果有旧任务在跑，先取消
            if current_chat_task and not current_chat_task.done():
                current_chat_task.cancel()

            try:
                current_bot = BotFactory.get_bot(model_name, page)
                current_bot.activate_tab()

                # 创建后台任务运行流式对话，不阻塞主循环
                current_chat_task = asyncio.create_task(
                    handle_chat_stream(websocket, current_bot, user_msg)
                )

            except Exception as e:
                await websocket.send_text(f"[Error]: {str(e)}")
                await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        print("前端已断开连接")
        if current_chat_task: current_chat_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)