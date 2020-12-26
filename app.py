import datetime
import os
import json
from flask import Flask, request, abort
from flask.logging import create_logger

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, StickerMessage, TextSendMessage, PostbackEvent,
    QuickReply, PostbackAction, ConfirmTemplate, TemplateSendMessage, StickerSendMessage
)
from google.cloud import datastore
import config

from send_email import send_notice
from quick_buttons import number_buttons, menu_buttons, proceed_irregular_buttons, teacher_buttons
from chat import torchBot

app = Flask(__name__)
log = create_logger(app)
client = datastore.Client()
line_bot_api = LineBotApi(config._LINE_TOKEN)
handler = WebhookHandler(config._LINE_SECRET)


# rich_menu = ["欠席 / Absence", "遅刻 / Tardiness", "早退 / Leave early",
# "連絡、質問 / Contact, Question", "回答、提出 / Answer, Submit", "その他 / Others"]

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
    if user and (user["isEnglish"] is True):
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
            "createdAt": event.timestamp,
        })
        client.put(user)
        confirm_template = ConfirmTemplate(text="子どもの登録がまだっぽいので、まずは言語を選んでください。Seems like you haven't registered your child yet. Firstly select your language please.", actions=[
            PostbackAction(label='日本語', data="language_japanese",
                           display_text='日本語'),
            PostbackAction(label='English',
                           data="language_english", display_text='English'),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm language', template=confirm_template)
        line_bot_api.reply_message(event.reply_token, template_message)
    elif user["child_name"] == "":
        if user["classroom"] == -1:
            client.delete(user_key)
            messages = [TextSendMessage(text=words["bug"]), StickerSendMessage(
                package_id="11538",
                sticker_id="51626499")]
            line_bot_api.reply_message(event.reply_token, messages)
        else:
            with client.transaction():
                user["child_name"] = event.message.text
                client.put(user)
            messages = [StickerSendMessage(package_id="11537", sticker_id="52002745"),
                        TextSendMessage(text=words["registerCompleted"],
                                        quick_reply=QuickReply(items=menu_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)
    # elif (action is None) and (event.message.text in rich_menu[3:6]):
    #     messages = [TextSendMessage(text=words["underConstruction"]), StickerSendMessage(
    #         package_id="11538",
    #         sticker_id="51626508")]
    #     line_bot_api.reply_message(event.reply_token, messages)
    elif action is not None:
        print("action is not none in message")
        if action["when"] == "":
            client.delete(action_key)
            messages = [StickerSendMessage(
                package_id="11538", sticker_id="51626499"),
                TextSendMessage(text=words["bug"],
                                quick_reply=QuickReply(items=menu_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)
        elif action["reason"] == "":
            with client.transaction():
                action["reason"] = event.message.text
                client.put(action)
            confirm_submit = words["confirmSubmit"]
            submit_type = words[action["category"]]
            date_time = words["dateTime"]
            when = action["when"]
            reason_key = words["reason"]
            reason_value = action["reason"]
            confirm_template = ConfirmTemplate(text=f"{confirm_submit} {submit_type} {date_time}: {when}, {reason_key}: {reason_value}", actions=[
                PostbackAction(label=words["yes"], data="submit_yes",
                               display_text=words["yes"]),
                PostbackAction(label=words["cancel"], data="action_cancel",
                               display_text=words["cancel"]),
            ])
            template_message = TemplateSendMessage(
                alt_text='Confirm submit', template=confirm_template)
            line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text == "Teacher on":
        with client.transaction():
            user["isTeacher"] = True
            client.put(user)
        messages = [StickerSendMessage(
            package_id="11538", sticker_id="51626514"),
            TextSendMessage(text=words["teacherMode"] + ": ON",
                            quick_reply=QuickReply(items=teacher_buttons(words)))]
        line_bot_api.reply_message(event.reply_token, messages)
    elif user["isTeacher"] is True:
        config_key = client.key("ConfigKind", "email")
        configuration = client.get(config_key)
        if configuration["email"] == "":
            with client.transaction():
                configuration["email"] = event.message.text
                client.put(configuration)
            messages = [StickerSendMessage(
                package_id="11537", sticker_id="52002768"),
                TextSendMessage(text=words["setEmailDone"],
                                quick_reply=QuickReply(items=teacher_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)
        else:
            with client.transaction():
                user["isTeacher"] = False
                client.put(user)
            messages = [StickerSendMessage(package_id="11538",
                                           sticker_id="51626494"),
                        TextSendMessage(text=words["teacherMode"] + ": OFF",
                                        quick_reply=QuickReply(items=menu_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)
    else:
        messages = []
        torch_message = torchBot(event.message.text)
        messages.append(TextSendMessage(text=torch_message,
                                        quick_reply=QuickReply(items=menu_buttons(words))))
        if "I don't know" in torch_message:
            messages.insert(0, StickerSendMessage(
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
    if user["isEnglish"] is True:
        words = english_words
    else:
        words = japanese_words
    if user["child_name"] == "":
        if "language_" in event.postback.data:
            if event.postback.data == "language_english":
                with client.transaction():
                    user["isEnglish"] = True
                    client.put(user)
                words = english_words
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=words["grade"],
                    quick_reply=QuickReply(
                        items=number_buttons(6, "grade"))))
        elif "grade_" in event.postback.data:
            with client.transaction():
                user["grade"] = int(event.postback.data[6:7])
                client.put(user)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=words["classroom"],
                    quick_reply=QuickReply(
                        items=number_buttons(5, "classroom"))))
        elif "classroom_" in event.postback.data:
            with client.transaction():
                user["classroom"] = int(event.postback.data[10:11])
                client.put(user)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["childName"]))
    elif "menu_" in event.postback.data:
        category = event.postback.data[5:]
        if category == "absence":
            choices = ["chooseDate",
                       "irregular_datetime_absence", "date"]
        elif category == "tardiness":
            choices = ["chooseDateTime",
                       "irregular_datetime_tardiness", "datetime"]
        elif category == "leave_early":
            choices = ["chooseDateTime",
                       "irregular_datetime_leave_early", "datetime"]
        action_key = client.key("ActionKind", user_id)
        action = datastore.Entity(key=action_key)
        action.update(
            {
                "category": category,
                "when": "",
                "reason": "",
                "createdAt": event.timestamp,
            }
        )
        client.put(action)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=words[f"proceed_{category}"],
                quick_reply=QuickReply(
                    items=proceed_irregular_buttons(words, choices))))
    elif action is not None:
        print("action is not none in postback")
        if "irregular_datetime_" in event.postback.data:
            with client.transaction():
                if "absence" in event.postback.data:
                    action["when"] = event.postback.params['date']
                else:
                    action["when"] = event.postback.params['datetime']
                action["previous_message"] = "askReason"
                client.put(action)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["askReason"]))
        elif event.postback.data == "submit_yes":
            config_key = client.key("ConfigKind", "email")
            configuration = client.get(config_key)
            send_notice(
                user["child_name"], user["grade"], user["classroom"],
                action["category"], action["when"], action["reason"],
                configuration["email"])
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
                    "createdAt": event.timestamp,
                }
            )
            client.put(sent_action)
            client.delete(action_key)
            messages = [StickerSendMessage(package_id="11538", sticker_id="51626501"),
                        TextSendMessage(text=words[action["category"] + "Sent"],
                                        quick_reply=QuickReply(items=menu_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)
        elif event.postback.data == "action_cancel":
            client.delete(action_key)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["cancelDone"],
                                quick_reply=QuickReply(items=menu_buttons(words))))
    elif "teacher_" in event.postback.data:
        if "seeActions" in event.postback.data:
            query = client.query(kind="SentActionKind")
            if event.postback.data == "seeActionsByDate":
                query.add_filter("registerd_date", "=",
                                 event.postback.params['date'])
            results = list(query.fetch())
            notices = []
            for result in results:
                child = result["child"]
                grade = result["grade"]
                classroom = result["classroom"]
                category = result["category"]
                when = result["when"]
                reason = result["reason"]
                time = datetime.datetime.fromtimestamp(
                    result["createdAt"] / 1e3)
                notices.append(
                    f"名前(Name): {child}, {grade}年(Grade), {classroom}組(Classroom), 種類(Category): {category}, 日時(When): {when}, 理由(Reason): {reason}, 登録日時(Registered Time): {time}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='\n\n'.join(notices), quick_reply=QuickReply(
                    items=teacher_buttons(words))))
        elif "seeUsers" in event.postback.data:
            query = client.query(kind="UserKind")
            results = list(query.fetch())
            users = []
            for result in results:
                is_english = result["isEnglish"]
                is_teacher = result["isTeacher"]
                child_name = result["child_name"]
                grade = result["grade"]
                classroom = result["classroom"]
                time = datetime.datetime.fromtimestamp(
                    result["createdAt"] / 1e3)
                users.append(
                    f"名前：{child_name}、{grade}年 {classroom}組、Is English?:{is_english}、先生モード: {is_teacher}、登録日時: {time}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='\n\n'.join(users), quick_reply=QuickReply(
                    items=teacher_buttons(words))))
        elif "setEmail" in event.postback.data:
            config_key = client.key("ConfigKind", "email")
            configuration = datastore.Entity(key=config_key)
            configuration.update(
                {
                    "email": "",
                    "createdAt": event.timestamp,
                }
            )
            client.put(configuration)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["askEmail"]))
        elif "deleteUser" in event.postback.data:
            client.delete(user_key)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=words["deleteUserDone"]))
        elif "teacherOff" in event.postback.data:
            with client.transaction():
                user["isTeacher"] = False
                client.put(user)
            messages = [StickerSendMessage(
                package_id="11538", sticker_id="51626494"),
                TextSendMessage(text=words["teacherMode"] + ": OFF",
                                quick_reply=QuickReply(items=menu_buttons(words)))]
            line_bot_api.reply_message(event.reply_token, messages)


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
