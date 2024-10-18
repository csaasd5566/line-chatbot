# chat_history.py

# 模擬聊天記錄的模組
chat_history = [
    {"role": "system", "content": "You are a professional stock analyst, specializing in answering various questions from clients."}
]

# 追加新聊天記錄到歷史
def add_to_history(role, content):
    chat_history.append({"role": role, "content": content})
