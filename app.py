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


rich_menu = ["欠席 / Absence", "遅刻 / Tardiness", "早退 / Leave early", "連絡、質問 / Contact, Question", "回答、提出 / Answer, Submit", "その他 / Others"
             ]

with open('language/japanese.json') as japanese:
    japanese_words = json.load(japanese)
with open('language/english.json') as english:
    english_words = json.load(english)


@ app.route("/callback", methods=['POST'])
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


@ handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("message event", event)
    user_id = event.source.user_id
    user_key = client.key("UserKind", user_id)
    user = client.get(user_key)
    action_key = client.key("ActionKind", user_id)
    action = client.get(action_key)
    if (user is not None) and (user["isEnglish"] == True):
        words = english_words
    else:
        words = japanese_words
    if user is None:
        user = datastore.Entity(key=user_key)
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
            words = english_words
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
            TextSendMessage(
                text=words["registerCompleted"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["absence"], text=words["absence"]),
                            # action=DatetimePickerAction(
                            #     label=words["absence"], data="absence_date_postback", mode="date")
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["tardiness"], text=words["tardiness"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["leave_early"], text=words["leave_early"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["contact_question"], text=words["contact_question"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["answer_submit"], text=words["answer_submit"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["others"], text=words["others"]),
                        ),
                    ])))

    elif (action is None) and (event.message.text in [words["absence"], words["tardiness"], words["leave_early"]]):
        if event.message.text == words["absence"]:
            category = "absence"
        elif event.message.text == words["tardiness"]:
            category = "tardiness"
        else:
            category = "leave_early"
        action_key = client.key("ActionKind", user_id)
        action = datastore.Entity(key=action_key)
        action.update(
            {
                "category": category,
                "when": "",
                "reason": "",
            }
        )
        client.put(action)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["askReason"]))

    elif (action is not None) and (action["reason"] == ""):
        with client.transaction():
            action["reason"] = event.message.text
            client.put(action)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words["proceedAbsence"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=PostbackAction(
                                label=words["today"], data='absence_postback_today', displayText=words["today"]),
                        ),
                        QuickReplyButton(
                            action=DatetimePickerAction(
                                label=words["chooseDate"], data="absence_postback_date", mode="date")
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["cancel"], text=words["cancel"]),
                        ),
                    ])))
    elif (action is not None) and (event.message.text == words["cancel"]):
        client.delete(action_key)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["cancelDone"]))
    elif event.message.text == "Delete":
        client.delete(user_key)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="User deleted"))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words["feelFree"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["absence"], text=words["absence"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["tardiness"], text=words["tardiness"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["leave_early"], text=words["leave_early"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["contact_question"], text=words["contact_question"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["answer_submit"], text=words["answer_submit"]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["others"], text=words["others"]),
                        ),
                    ])))


@ handler.add(PostbackEvent)
def handle_postback(event):
    print("postback event", event)
    user_id = event.source.user_id
    user_key = client.key("UserKind", user_id)
    user = client.get(user_key)
    action_key = client.key("ActionKind", user_id)
    action = client.get(action_key)
    if (user is not None) and (user["isEnglish"] == True):
        words = english_words
    else:
        words = japanese_words
    if event.postback.data[0:17] == "absence_postback_":
        if event.postback.data == "absence_postback_today":
            print("not yet done")
        elif event.postback.data == "absence_postback_date":
            when = event.postback.params['date']
        with client.transaction():
            action["when"] = when
            client.put(action)
        absenceConfirm = words["absenceConfirm"]
        dateTimeKey = words["dateTime"]
        whenValue = action["when"]
        reasonKey = words["reason"]
        reasonValue = action["reason"]
        confirm_template = ConfirmTemplate(text=f"{absenceConfirm} --- {dateTimeKey}: {whenValue}, {reasonKey}: {reasonValue}", actions=[
            PostbackAction(
                label=words["yes"], data="absence_execte_postback", displayText=words["yes"]),
            MessageAction(
                label=words["cancel"], text=words["cancel"]),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm absence', template=confirm_template)
        line_bot_api.reply_message(event.reply_token, template_message)

    elif event.postback.data == "absence_execte_postback":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="absence_execte_postback"))
        # elif event.postback.data == 'datetime_postback':
        #     line_bot_api.reply_message(
        #         event.reply_token, TextSendMessage(text=event.postback.params['datetime']))
        # elif event.postback.data == 'date_postback':
        #     line_bot_api.reply_message(
        #         event.reply_token, TextSendMessage(text=event.postback.params['date']))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)))
