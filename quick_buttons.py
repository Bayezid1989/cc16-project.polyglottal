from linebot.models import (
    QuickReplyButton, PostbackAction, DatetimePickerAction)


def number_buttons(maxNumber, grade_classroom):
    quick_buttons = []
    number = 1
    while number <= maxNumber:
        quick_buttons.append(QuickReplyButton(
            action=PostbackAction(
                label=number, data=f"{grade_classroom}_" + str(number), display_text=number)
        ))
        number += 1
    return quick_buttons


def menu_buttons(words):
    quick_buttons = []
    for option in ["absence", "tardiness", "leave_early",
                   "contactQuestion", "answerSubmit", "others"]:
        quick_buttons.append(QuickReplyButton(
            action=PostbackAction(
                label=words[option], data="menu_" + option, display_text=words[option])
        ))
    return quick_buttons


def proceed_irregular_buttons(words, choices):
    return [
        QuickReplyButton(
            action=DatetimePickerAction(
                label=words[choices[0]], data=choices[1], mode=choices[2])
        ),
        QuickReplyButton(
            action=PostbackAction(
                label=words["cancel"], data="action_cancel", display_text=words["cancel"]),
        ),
    ]


def teacher_buttons(words):
    quick_buttons = [QuickReplyButton(
        action=DatetimePickerAction(
            label=words["seeActionsByDate"], data="seeActionsByDate", mode="date")
    )]
    for option in ["seeActionsAll", "seeUsers", "setEmail", "deleteUser", "teacherOff"]:
        quick_buttons.append(QuickReplyButton(
            action=PostbackAction(
                label=words[option], data="teacher_" + option, display_text=words[option])
        ))
    return quick_buttons
