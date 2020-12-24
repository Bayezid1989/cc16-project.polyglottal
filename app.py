from flask import Flask, request, abort
from flask.logging import create_logger

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, MessageAction, TextMessage, StickerMessage, TextSendMessage, PostbackEvent, QuickReply, QuickReplyButton, PostbackAction, DatetimePickerAction, ConfirmTemplate, TemplateSendMessage, StickerSendMessage
)
from google.cloud import datastore
from dotenv import load_dotenv
import config
import datetime
import os
import json
import sendEmail
from chat import torchBot

app = Flask(__name__)
log = create_logger(app)
client = datastore.Client()
line_bot_api = LineBotApi(config._LINE_TOKEN)
handler = WebhookHandler(config._LINE_SECRET)
email_address = config.SEND_EMAIL


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
            "isTeacher": False,
            "child_name": "",
            "grade": -1,
            "classroom": -1,
            "previous_message": "register_language",
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

    elif (user["previous_message"] == "register_language") and (event.message.text in ["日本語", "English"]):
        if event.message.text == "English":
            with client.transaction():
                user["isEnglish"] = True
                user["previous_message"] = "childName"
                client.put(user)
            words = english_words
        else:
            with client.transaction():
                user["previous_message"] = "childName"
                client.put(user)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["childName"]))
    elif user["previous_message"] == "childName":
        with client.transaction():
            user["child_name"] = event.message.text
            user["previous_message"] = "grade"
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
    elif (user["previous_message"] == "grade") and (event.message.text in ["1", "2", "3", "4", "5", "6"]):
        with client.transaction():
            user["grade"] = int(event.message.text)
            user["previous_message"] = "classroom"
            client.put(user)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words["classroom"],
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
                    ])))
    elif (user["previous_message"] == "classroom") and (event.message.text in ["1", "2", "3", "4", "5"]):
        with client.transaction():
            user["classroom"] = int(event.message.text)
            user["previous_message"] = "registerCompleted"
            client.put(user)
        messages = [TextSendMessage(text=words["registerCompleted"]), StickerSendMessage(
            package_id="11537",
            sticker_id="52002745")]
        line_bot_api.reply_message(event.reply_token, messages)
    elif (action is None) and (event.message.text in rich_menu[0:3]):
        if event.message.text == rich_menu[0]:
            category = "Absence"
            choices = ["today", "tomorrow", "chooseDate",
                       '{"key": "choose_datetime", "value": "absence"}', "date"]
        elif event.message.text == rich_menu[1]:
            category = "Tardiness"
            choices = ["1h", "noon", "chooseDateTime",
                       '{"key": "choose_datetime", "value": "tardiness"}', "datetime"]
        else:
            category = "Leave_early"
            choices = ["1hLeave", "noonLeave", "chooseDateTime",
                       '{"key": "choose_datetime", "value": "leave_early"}', "datetime"]
        action_key = client.key("ActionKind", user_id)
        action = datastore.Entity(key=action_key)
        action.update(
            {
                "category": category,
                "when": "",
                "reason": "",
                "previous_message": f"proceed{category}"
            }
        )
        client.put(action)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words[f"proceed{category}"],
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(
                            action=MessageAction(
                                label=words[choices[0]], text=words[choices[0]]),
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words[choices[1]], text=words[choices[1]]),
                        ),
                        QuickReplyButton(
                            action=DatetimePickerAction(
                                label=words[choices[2]], data=choices[3], mode=choices[4])
                        ),
                        QuickReplyButton(
                            action=MessageAction(
                                label=words["cancel"], text=words["cancel"]),
                        ),
                    ])))
    elif (action is None) and (event.message.text in rich_menu[3:6]):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["underConstruction"]))
    elif (action is not None):
        if "proceed" in action["previous_message"]:
            if (action["previous_message"] == "proceedAbsence") and (event.message.text in [words["today"], words["tomorrow"]]):
                target_date = datetime.date.today()
                if event.message.text == words["tomorrow"]:
                    target_date = target_date + datetime.timedelta(days=1)
                with client.transaction():
                    action["when"] = str(target_date)
                    action["previous_message"] = "askReason_absence"
                    client.put(action)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=words["askReason"]))
            elif event.message.text in [words["1h"], words["noon"], words["1hLeave"], words["noonLeave"]]:
                lower_category = action["category"].lower()
                with client.transaction():
                    action["when"] = event.message.text
                    action["previous_message"] = f"askReason_{lower_category}"
                    client.put(action)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=words["askReason"]))
            else:
                client.delete(action_key)
                messages = [TextSendMessage(text=words["bug"]), StickerSendMessage(
                    package_id="11538",
                    sticker_id="51626499")]
                line_bot_api.reply_message(event.reply_token, messages)
        elif "askReason" in action["previous_message"]:
            with client.transaction():
                action["reason"] = event.message.text
                action["previous_message"] = "confirmAbsTarLea"
                client.put(action)
            confirmAbsTarLea = words["confirmAbsTarLea"]
            lower_category = action["category"].lower()
            submitType = words[lower_category]
            dateTimeKey = words["dateTime"]
            whenValue = action["when"]
            reasonKey = words["reason"]
            reasonValue = action["reason"]
            confirm_template = ConfirmTemplate(text=f"{confirmAbsTarLea} {submitType} {dateTimeKey}: {whenValue}, {reasonKey}: {reasonValue}", actions=[
                MessageAction(label=words["yes"], text=words["yes"]),
                MessageAction(label=words["cancel"], text=words["cancel"]),
            ])
            template_message = TemplateSendMessage(
                alt_text='Confirm', template=confirm_template)
            line_bot_api.reply_message(event.reply_token, template_message)

        elif (action["previous_message"] == "confirmAbsTarLea") and (event.message.text == words["yes"]):
            sendEmail.sendAbsence(
                user["child_name"], user["grade"], user["classroom"], action["category"], action["when"], action["reason"], email_address)
            sent_action_key = client.key("SentActionKind", event.timestamp)
            sent_action = datastore.Entity(key=sent_action_key)
            sent_action.update(
                {
                    "child": user["child_name"],
                    "grade": user["grade"],
                    "classroom": user["classroom"],
                    "category": action["category"],
                    "when": action["when"],
                    "reason": action["reason"],
                    "registerd_date": str(datetime.date.today()),
                    "timestamp": event.timestamp,
                }
            )
            client.put(sent_action)
            client.delete(action_key)
            lower_category = action["category"].lower()
            messages = [TextSendMessage(text=words[f"{lower_category}Sent"]), StickerSendMessage(
                package_id="11538",
                sticker_id="51626501")]
            line_bot_api.reply_message(event.reply_token, messages)
        elif event.message.text == words["cancel"]:
            client.delete(action_key)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["cancelDone"]))
        else:
            client.delete(action_key)
            messages = [TextSendMessage(text=words["bug"]), StickerSendMessage(
                package_id="11538",
                sticker_id="51626499")]
            line_bot_api.reply_message(event.reply_token, messages)
    elif event.message.text == "Teacher on":
        with client.transaction():
            user["isTeacher"] = True
            user["previous_message"] = "teacherOn"
            client.put(user)
        messages = [TextSendMessage(text="先生モード、ON"), StickerSendMessage(
            package_id="11538",
            sticker_id="51626514")]
        line_bot_api.reply_message(event.reply_token, messages)
    elif user["isTeacher"] == True:
        if event.message.text == "See users":
            query = client.query(kind="UserKind")
            results = list(query.fetch())
            messages = []
            for result in results:
                isEnglish = result["isEnglish"]
                isTeacher = result["isTeacher"]
                child_name = result["child_name"]
                grade = result["grade"]
                classroom = result["classroom"]
                time = datetime.datetime.fromtimestamp(
                    result["timestamp"] / 1e3)
                messages.append(TextSendMessage(
                    text=f"名前：{child_name}、{grade}年 {classroom}組、Is English?:{isEnglish}、先生モード: {isTeacher}、登録日時: {time}"))
            line_bot_api.reply_message(event.reply_token, messages)
        elif "See actions" in event.message.text:
            query = client.query(kind="SentActionKind")
            if "today" in event.message.text:
                query.add_filter("registerd_date", "=",
                                 str(datetime.date.today()))
            elif "yesterday" in event.message.text:
                query.add_filter("registerd_date", "=",
                                 str(datetime.date.today() - datetime.timedelta(days=1)))
            results = list(query.fetch())
            messages = []
            for result in results:
                child = result["child"]
                grade = result["grade"]
                classroom = result["classroom"]
                category = result["category"]
                when = result["when"]
                reason = result["reason"]
                time = datetime.datetime.fromtimestamp(
                    result["timestamp"] / 1e3)
                messages.append(TextSendMessage(
                    text=f"子ども: {child}、{grade}年 {classroom}組、内容：{category}、{when}、{reason}、登録日時: {time}"))
            line_bot_api.reply_message(event.reply_token, messages)
        elif event.message.text == "Teacher off":
            with client.transaction():
                user["isTeacher"] = False
                user["previous_message"] = "teacherOff"
                client.put(user)
            messages = [TextSendMessage(text="先生モード、OFF"), StickerSendMessage(
                package_id="11538",
                sticker_id="51626494")]
            line_bot_api.reply_message(event.reply_token, messages)
        # elif event.message.text == "Set email":
        elif event.message.text == "Delete user":
            client.delete(user_key)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="User deleted"))
        else:
            messages = []
            torch_message = torchBot(event.message.text)
            messages.append(TextSendMessage(text=torch_message))
            if "I don't know" in torch_message:
                messages.append(StickerSendMessage(
                    package_id="11537",
                    sticker_id="52002744"))
            line_bot_api.reply_message(event.reply_token, messages)
    else:
        messages = []
        torch_message = torchBot(event.message.text)
        messages.append(TextSendMessage(text=torch_message))
        if "I don't know" in torch_message:
            messages.append(StickerSendMessage(
                package_id="11537",
                sticker_id="52002744"))
        line_bot_api.reply_message(event.reply_token, messages)


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
    if json.loads(event.postback.data)["key"] == "choose_datetime":
        value = json.loads(event.postback.data)["value"]
        with client.transaction():
            if value == "absence":
                action["when"] = event.postback.params['date']
            else:
                action["when"] = event.postback.params['datetime']
            action["previous_message"] = f"askReason_{value}"
            client.put(action)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=words["askReason"]))


@ handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id="11537",
            sticker_id="52002753")
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)))
