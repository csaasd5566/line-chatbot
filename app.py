import openai
import time
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, TextMessage
from linebot.v3.webhook import WebhookHandler, MessageEvent
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging.models import ReplyMessageRequest, PushMessageRequest
import json
import logging
import os
from chat_history import chat_history  # 引入聊天记录模块
from dotenv import load_dotenv
app = Flask(__name__)

# 設定 LINE API
LINE_CHANNEL_ACCESS_TOKEN = 'R4SST5q9sCTEvKInzc6UI6v5WMNTF7/mVRWDqOSvw3U+DJYDidAaEuC7ufLW8XsPAoeYnwEmSOa9/hCN9t/zFE4ibHaQJEiiRfEym/g7tmiGPx3b7GSfcsZhRYouihZTbvmySB1oQU7/bzkXcALDUwdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'ff23d25e8776a10abb63d58e6b627a45'
load_dotenv()
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret=LINE_CHANNEL_SECRET)

# 設定 OpenAI API
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
#print(os.getenv("OPENAI_API_KEY"))
# 設定日志
logging.basicConfig(level=logging.INFO)
# 初始化 MongoDB
@app.route("/webhook", methods=['POST'])  # 确保路由为 /webhook
def linebot():
    logging.info("linebot function called")
    body = request.get_data(as_text=True)
    #logging.info(f"Request body: {body}")
    try:
        signature = request.headers['X-Line-Signature']
        logging.info(f"Signature: {signature}")
        handler.handle(body, signature)
        
        json_data = json.loads(body)
        tk = json_data['events'][0]['replyToken']
        msg = json_data['events'][0]['message']['text']
        
        
        logging.info(f"Message from user: {msg}")
        
        reply_msg = ''
        # 檢查用戶狀態
        # 將訊息發送給 OpenAI
        if msg.startswith('$股票'):
            stock_query = msg.replace('$股票', '').strip()  # 提取後面的查詢內容
            try:
                model = "gpt-4o"
                messages = chat_history.copy()  # 复制历史记录，避免修改原始数据
                messages.append({"role": "user", "content": stock_query})
                #logging.info(f"Messages to OpenAI: {messages}")
                messages.append({"role":"user","content":"Based on the question I provided, organize the company name and the information I want to query into JSON,and only reply with the JSON,and reply in Traditional Chinese."})
                result_simple_chat = client.chat.completions.create(
                  model=model,
                  messages = messages,
                )
                # 正確地访问回覆訊息
                reply_msg = result_simple_chat.choices[0].message.content.strip()
                logging.info(f"Reply from OpenAI(1): {reply_msg}")
                messages.append({"role":"user","content":f"I will provide you with a JSON that includes the company and query item. Generate a piece of code to query the company's query item, use the yfinance package to fetch the data, store the output result in the variable result, and only reply with the code.,{reply_msg}"})
                result_chat= client.chat.completions.create(
                  model=model,
                  messages = messages,
                )
                chat=result_chat.choices[0].message.content.strip()
                clean_code = chat.replace('python', '').replace('```', '').strip()
                logging.info(f"Reply from OpenAI: {clean_code}")
            except Exception as e:
                logging.error(f"Error calling OpenAI API: {e}")
                reply_msg = "對不起，無法處理您的請求。"
    
            text_message = TextMessage(text=reply_msg)
            #logging.info(f"Reply message: {reply_msg}")
    
            # 延迟已读
            #time.sleep(1)  # 延迟3秒，模拟已读行为
    
            # 回复消息
            # 初始化一个全局变量来储存结果
            global_vars = {}
        
            # 在全局命名空間中執行代碼，將變數存儲在 global_vars 中
            exec(clean_code, global_vars)
        
            # 檢查 global_vars 中是否有 'result' 變數
            if 'result' in global_vars:
                result_value = global_vars['result']
    
                # 確保 result 是可轉換為字串的類型
                if isinstance(result_value, (str, int, float)):
                    result_str = str(result_value)
                else:
                    # 如果是複雜對象，如 DataFrame，將其轉換為字串
                    result_str = str(result_value)
        
                logging.info(f"The result is: {result_str}")
                
                # 將結果發送回用戶
                messages.append({"role":"user","content":f"I will return the calculated data to the user and advise them on which indicators to look at in combination, as well as whether it is a good entry point. Please reply in Traditional Chinese.{result_str}"})
                last_chat= client.chat.completions.create(
                  model=model,
                  messages = messages,
                )
                reply_text = last_chat.choices[0].message.content.strip()
                text_message = TextMessage(text=reply_text)
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=tk,
                        messages=[text_message]
                    )
                )
            else:
                logging.error("The result variable was not found.")
                text_message = TextMessage(text="無法處理請求，找不到結果變數")
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=tk,
                        messages=[text_message]
                    )
                )

        
    except InvalidSignatureError:
        logging.error("Invalid signature. Check your channel secret/access token.")
        abort(400)
    except Exception as e:
        logging.error(f"General Error: {e}")
        abort(500)
    return 'OK'

if __name__ == "__main__":
    logging.info("Starting Flask server")
    app.run(port=3000)
