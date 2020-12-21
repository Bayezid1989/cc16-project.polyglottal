from flask import Flask, request, abort
from flask.logging import create_logger

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from google.cloud import datastore
import config
import datetime
import os

app = Flask(__name__)
log = create_logger(app)
client = datastore.Client()
line_bot_api = LineBotApi(config.token)
handler = WebhookHandler(config.secret)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    log.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_key = client.key("UserTable", user_id) # kindとidを引数にKeyを取得
    user_entity = client.get(user_key) # Keyを引数にEntityを取得
    if user_entity is None:
        user_entity = datastore.Entity(key=user_key, exclude_from_indexes=("timestamp",))
        msg = "はじめまして！"
    else:
        timestamp = user_entity["timestamp"]
        ts = datetime.datetime.fromtimestamp(timestamp/1000)
        msg = "{}年{}月{}日{}時{}分以来ですね！".format(ts.year, ts.month, ts.day, ts.hour, ts.minute)
    user_entity.update({ # Entityの更新
        "timestamp": event.timestamp
    })
    client.put(user_entity) # 引数のEntityをDatastoreに保存
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))