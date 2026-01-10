# backend/server.py
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from crawler_base import BotFactory, ChromiumPage

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化浏览器 (单例)
try:
    # 建议使用特定端口，防止和其他浏览器冲突
    # from DrissionPage import ChromiumOptions
    # co = ChromiumOptions().auto_port()
    # page = ChromiumPage(addr_or_opts=co)
    page = ChromiumPage()
    print("浏览器后端初始化成功")
except Exception as e:
    print(f"浏览器启动失败: {e}")
    page = None

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    if not page:
        await websocket.send_text("Error: 后端浏览器未启动")
        await websocket.close()
        return

    try:
        while True:
            # 1. 接收前端 JSON
            data = await websocket.receive_json()
            model_name = data.get("model")
            user_msg = data.get("message")

            if not model_name or not user_msg:
                continue

            try:
                # 2. 获取 Bot
                bot = BotFactory.get_bot(model_name, page)

                # 激活标签页 (同步操作)
                bot.activate_tab()

                # 3. 流式传输
                # stream_chat 是同步生成器，在 for 循环中必须手动让出 CPU 时间
                iterator = bot.stream_chat(user_msg)

                for char in iterator:
                    # 发送字符
                    await websocket.send_text(char)
                    # 【重要】防止阻塞主线程，保持 WebSocket 心跳
                    await asyncio.sleep(0)

                # 4. 结束标志
                await websocket.send_text("[DONE]")

            except Exception as e:
                print(f"处理出错: {e}")
                await websocket.send_text(f"[Error]: {str(e)}")
                await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        print("前端已断开连接")
    except Exception as e:
        print(f"WebSocket 异常: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)