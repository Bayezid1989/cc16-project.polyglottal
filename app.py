from flask import Flask, request, abort
from flask.logging import create_logger

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, MessageAction, TextMessage, TextSendMessage, PostbackEvent, QuickReply, QuickReplyButton, PostbackAction, DatetimePickerAction, ConfirmTemplate, TemplateSendMessage
)
from google.cloud import datastore
from dotenv import load_dotenv
import config
import datetime
import os
import json

app = Flask(__name__)
log = create_logger(app)
client = datastore.Client()
line_bot_api = LineBotApi(config._LINE_TOKEN)
handler = WebhookHandler(config._LINE_SECRET)


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
    print("event", event)
    user_id = event.source.user_id
    complete_key = client.key("UserKind", user_id)
    user = client.get(complete_key)
    if (user is not None) and (user["isEnglish"] == True):
        with open('language/english.json') as english:
            words = json.load(english)
    else:
        with open('language/japanese.json') as japanese:
            words = json.load(japanese)
    if user is None:
        user = datastore.Entity(key=complete_key)
        user.update({
            "isEnglish": False,
            "child_name": "",
            "grade": -1,
            "class": -1,
            "timestamp": event.timestamp,
        })
        client.put(user)
        confirm_template = ConfirmTemplate(text='あなた登録がまだっぽいですね。まずは言語を選んでください。Select your language please.', actions=[
            MessageAction(label='日本語', text='日本語'),
            MessageAction(label='English', text='English'),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm language', template=confirm_template)
        line_bot_api.reply_message(event.reply_token, template_message)

    elif (user["child_name"] == "") and (event.message.text in ["日本語", "English"]):
        if event.message.text == "English":
            with client.transaction():
                user["isEnglish"] = True
                client.put(user)
            with open('language/english.json') as english:
                words = json.load(english)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["childName"]))
    elif user["child_name"] == "":
        with client.transaction():
            user["child_name"] = event.message.text
            client.put(user)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words["grade"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label="1", text="1"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="2", text="2"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="3", text="3"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="4", text="4"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="5", text="5"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="6", text="6"),
                        )
                    ])))
    elif (user["grade"] == -1) and (event.message.text in ["1", "2", "3", "4", "5", "6"]):
        with client.transaction():
            user["grade"] = int(event.message.text)
            client.put(user)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words["class"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label="1", text="1"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="2", text="2"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="3", text="3"),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label="4", text="4"),
                        ),
                    ])))
    elif (user["class"] == -1) and (event.message.text in ["1", "2", "3", "4"]):
        with client.transaction():
            user["class"] = int(event.message.text)
            client.put(user)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["registerCompleted"]))
    elif event.message.text == "Delete":
        client.delete(complete_key)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="User deleted"))
    else:
        message = "I don't know."
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
