import asyncio
import os
import json
import glob
import time
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crawler_base import BotFactory, ChromiumPage

# --- 配置 ---
HISTORY_DIR = "history_storage"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 数据模型 ---
class Message(BaseModel):
    role: str
    content: str
    timestamp: float

class ChatSession(BaseModel):
    id: str
    title: str  # 对话标题
    model: str
    messages: List[Message]
    updated_at: float

# --- 历史记录 API ---

@app.get("/api/history")
async def get_history_list():
    """获取所有对话的历史列表（按时间倒序）"""
    sessions = []
    files = glob.glob(os.path.join(HISTORY_DIR, "*.json"))

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                # 只返回列表需要的摘要信息，不返回所有 messages 以减少流量
                sessions.append({
                    "id": data.get("id"),
                    "title": data.get("title", "New Chat"),
                    "model": data.get("model"),
                    "updated_at": data.get("updated_at", 0)
                })
        except Exception as e:
            print(f"Error reading file {f}: {e}")
            continue

    # 按更新时间倒序排列
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return sessions

@app.get("/api/history/{chat_id}")
async def get_chat_detail(chat_id: str):
    """获取指定对话的完整内容"""
    file_path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/history")
async def save_chat(session: ChatSession):
    """保存或更新对话"""
    file_path = os.path.join(HISTORY_DIR, f"{session.id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            # model_dump() 是 pydantic v2 写法, v1 使用 dict()
            # 为了兼容性，这里使用 jsonable_encoder 或者直接 dict()
            json.dump(session.dict(), f, ensure_ascii=False, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/{chat_id}")
async def delete_chat(chat_id: str):
    """删除对话"""
    file_path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Chat not found")

# --- WebSocket & 浏览器逻辑 (保持不变) ---

# 初始化浏览器
# --- WebSocket & 浏览器逻辑 ---

# 初始化浏览器
try:
    page = ChromiumPage()
    print("浏览器后端初始化成功")
except Exception as e:
    print(f"浏览器启动失败: {e}")
    page = None

# 使用字典来管理并发任务和Bot实例
# Key: model_name, Value: Task
active_tasks = {}
# Key: model_name, Value: Bot Instance
active_bots = {}

async def handle_chat_stream(websocket: WebSocket, bot, message: str, model_name: str):
    try:
        async for content in bot.stream_chat(message):
            # 修改点：发送 JSON 对象，包含 model 标识，以便前端区分是哪个模型在说话
            await websocket.send_json({
                "type": "chunk",
                "model": model_name,
                "content": content
            })

        # 结束信号也带上 model
        await websocket.send_json({
            "type": "done",
            "model": model_name
        })

    except asyncio.CancelledError:
        print(f"任务被取消: {model_name}")
        # 即使取消，最好也发个信号让前端释放状态
        await websocket.send_json({"type": "done", "model": model_name})
    except Exception as e:
        print(f"流式传输错误 ({model_name}): {e}")
        await websocket.send_json({
            "type": "error",
            "model": model_name,
            "content": str(e)
        })

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    if not page:
        await websocket.send_json({"type": "error", "content": "Error: 后端浏览器未启动"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            # 1. 停止指令 (针对特定模型停止，或者全部停止)
            if msg_type == "stop":
                target_model = data.get("model")
                if target_model and target_model in active_tasks:
                    # 只停止指定模型的生成
                    if not active_tasks[target_model].done():
                        active_tasks[target_model].cancel()
                    if target_model in active_bots:
                        active_bots[target_model].stop_generation()
                continue

            # 2. 聊天请求
            model_name = data.get("model")
            user_msg = data.get("message")

            if not model_name or not user_msg:
                continue

            # 关键修改：只取消 **当前模型** 之前的任务，不影响其他模型
            if model_name in active_tasks and not active_tasks[model_name].done():
                active_tasks[model_name].cancel()

            try:
                # 获取或创建 Bot 实例 (这里假设 BotFactory 可以处理多 Tab 或并发)
                # 注意：如果 crawler_base 只有单 Tab，这里可能需要 bot.activate_tab()
                # 但为了并发，最好 bot 内部维护自己的 tab 对象
                current_bot = BotFactory.get_bot(model_name, page)
                active_bots[model_name] = current_bot

                # 激活该模型的 Tab (如果是基于浏览器的话，物理层面可能还是会有焦点抢占，但逻辑上已分离)
                # current_bot.activate_tab()

                # 创建新任务并存入字典
                task = asyncio.create_task(
                    handle_chat_stream(websocket, current_bot, user_msg, model_name)
                )
                active_tasks[model_name] = task

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "model": model_name,
                    "content": str(e)
                })

    except WebSocketDisconnect:
        print("前端已断开连接")
        # 清理所有任务
        for task in active_tasks.values():
            if not task.done():
                task.cancel()

if __name__ == "__main__":
    import uvicorn
    # 确保文件夹存在
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    uvicorn.run(app, host="0.0.0.0", port=8000)