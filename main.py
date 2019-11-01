import vk_api
import random
import config
import sqlite3
import string

from vk_api.longpoll import VkLongPoll, VkEventType

vk_session = vk_api.VkApi(token=config.token)

longpoll = VkLongPoll(vk_session)

vk = vk_session.get_api()

conn = sqlite3.connect(config.sqlite_path)
c = conn.cursor()


def generate_user_password():
    password = ""
    for number in range(8):
        password += (string.ascii_letters + string.digits)[random.randint(0, 61)]
    return password


def get_user(user_id):
    cmd = "SELECT * FROM users WHERE user_id=%d" % user_id
    c.execute(cmd)
    return c.fetchone()


def register_new_user(user_id):
    cmd = "INSERT INTO users(user_id, state) VALUES (%d, '')" % user_id
    c.execute(cmd)
    conn.commit()
    cmd = "INSERT INTO user_info(user_id, user_password, is_dead, is_registered)" \
          " VALUES (%d, '%s', 0, 0)" % (user_id, generate_user_password())
    c.execute(cmd)
    conn.commit()


def set_user_state(user_id, state):
    cmd = "UPDATE users SET state='%s' WHERE user_id=%d" % (state, user_id)
    c.execute(cmd)
    conn.commit()


def get_user_state(user_id):
    cmd = "SELECT state FROM users WHERE user_id=%d" % user_id
    c.execute(cmd)
    return c.fetchone()[0]


def get_user_image(user_id):
    cmd = "SELECT user_image FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    return c.fetchone()[0]


def get_user_group(user_id):
    cmd = "SELECT user_group FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    return c.fetchone()[0]


def set_user_image(user_id, attachment):
    cmd = "UPDATE user_info SET user_image = '%s' WHERE user_id=%d" % (attachment, user_id)
    c.execute(cmd)
    conn.commit()


def set_user_group(user_id, group):
    cmd = "UPDATE user_info SET user_group = '%s' WHERE user_id=%d" % (group, user_id)
    c.execute(cmd)
    conn.commit()


def get_game_stage():
    cmd = "SELECT game_stage FROM game_info"
    c.execute(cmd)
    return c.fetchone()[0]


def set_game_stage(stage):
    cmd = "UPDATE game_info SET game_stage = %d" % stage
    c.execute(cmd)
    conn.commit()


def set_user_registration_status(user_id):
    cmd = "UPDATE user_info SET is_registered = 1 WHERE user_id = %d" % user_id
    c.execute(cmd)
    conn.commit()


def get_user_registration_status(user_id):
    cmd = "SELECT is_registered FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    return c.fetchone()[0]


def get_image_from_dialogue(cur_event):
    result = vk_session.method("messages.getById", {
        "message_ids": [cur_event.message_id],
        "group_id": config.group_id
    })
    try:
        photo = result['items'][0]['attachments'][0]['photo']
        return "photo{}_{}_{}".format(photo['owner_id'], photo['id'], photo['access_key'])
    except:
        return None


def send_messages_to_all_users(message):
    cmd = "SELECT user_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        vk.messages.send(
            user_id=item[0],
            message=message,
            random_id=random.randint(-1000000000, 1000000000)
        )


def send_messages_about_victim_to_all_users():
    cmd = "SELECT user_id, target_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        image, group = generate_message_about_victim(item[1])
        message = "Ваша цель:\n Группа:" + group + "\n Фотография: "
        vk.messages.send(
            user_id=item[0],
            message=message,
            attachment=image,
            random_id=random.randint(-1000000000, 1000000000)
        )


def generate_victims():
    cmd = "SELECT user_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        target = item[0]
        target_of_target = item[0]
        while target == item[0] or target_of_target == item[0]:
            new_target = result[random.randint(0, len(result)-1)][0]
            target = new_target
            cmd = "SELECT target_id FROM user_info WHERE user_id=%d" % target
            c.execute(cmd)
            target_of_target = c.fetchone()[0]
            print(target_of_target)

        cmd = "UPDATE user_info SET target_id = %d WHERE user_id = %d" % (target, item[0])
        c.execute(cmd)
        conn.commit()


def check_kill(user_id, message):
    cmd = "SELECT target_id FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    cmd = "SELECT user_password FROM user_info WHERE user_id = %d" % c.fetchone()[0]
    c.execute(cmd)
    result = c.fetchone()[0]
    print(result)
    print(message)
    if str(result) == message:
        return True
    return False


def change_victim(user_id):
    cmd = "SELECT target_id FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    victim_id = c.fetchone()[0]

    cmd = "SELECT target_id FROM user_info WHERE user_id = %d" % victim_id
    c.execute(cmd)
    new_target_id = c.fetchone()[0]

    cmd = "UPDATE user_info SET target_id=%d WHERE user_id = %d" % (new_target_id, user_id)
    c.execute(cmd)
    conn.commit()

    cmd = "UPDATE user_info SET is_dead=1 WHERE user_id = %d" % victim_id
    c.execute(cmd)
    conn.commit()

    return new_target_id


def generate_message_about_victim(victim_id):
    cmd = "SELECT user_image, user_group FROM user_info WHERE user_id=%d" % int(victim_id)
    c.execute(cmd)
    result = c.fetchone()
    return result[0], result[1]


# Получить количество выживших игроков
def check_alive():
    cmd = "SELECT * FROM user_info WHERE is_dead = 0"
    c.execute(cmd)
    result = c.fetchall()
    return len(result)


def get_user_password(user_id):
    cmd = "SELECT user_password FROM user_info WHERE user_id=%d" % user_id
    c.execute(cmd)
    return c.fetchone()[0]


def check_message_on_stage_zero(cur_event):
    message = cur_event.text.lower()
    user_id = cur_event.user_id
    print(str(cur_event.user_id) + ": " + message)

    if message == "привет":
        vk.messages.send(
            user_id=user_id,
            message="Привет! Я твой куратор в этом состязании. Пиши сюда, все, что с ним связано. Так же напиши"
                    " 'помощь', если захочешь узнать, что мне можно сказать",
            random_id=random.randint(-1000000000, 1000000000)
        )
    elif message == "регистрация":
        if get_user_registration_status(user_id) == 0:
            vk.messages.send(
                user_id=user_id,
                message="Отлично! Теперь отправьте мне фотографию себя, чтобы другие охотники смогли вас найти",
                random_id=random.randint(-1000000000, 1000000000)
            )
            set_user_state(user_id, "registration_image")
        else:
            vk.messages.send(
                user_id=user_id,
                message="Ты уже участвешь, жди начала..."
                        "\n(https://vk.com/id_000010010010000000000001)",
                random_id=random.randint(-1000000000, 1000000000)
            )

    # Администратор пишет определенные буквы в определнном регистре
    elif cur_event.text == "СмеНА сТадИи " + config.passwd:
        set_game_stage(1)
        send_messages_to_all_users("Внимание, игра началась!")
        generate_victims()
        send_messages_about_victim_to_all_users()

    else:
        if get_user_state(user_id) == "registration_image":
            dialogue_image = get_image_from_dialogue(cur_event)
            if dialogue_image is None:
                vk.messages.send(
                    user_id=user_id,
                    message="Слушай, тут нет фотографии, давай не пытаться обмануть друг-друга",
                    random_id=random.randint(-1000000000, 1000000000)
                )
            else:
                set_user_image(user_id, dialogue_image)
                set_user_state(user_id, "registration_group")
                vk.messages.send(
                    user_id=user_id,
                    message="Укажите группу в которой вы учитесь (Например: 3ПКС-17-1к) или, если вы преподаватель,"
                            " укажите, что вы преподаете",
                    random_id=random.randint(-1000000000, 1000000000)
                )
        elif get_user_state(user_id) == "registration_group":
            set_user_group(user_id, event.text)
            set_user_state(user_id, "")
            set_user_registration_status(user_id)
            vk.messages.send(
                user_id=user_id,
                message="Все, ты в игре, жди начала... Ах да, твой пароль: " + get_user_password(user_id) + ","
                                                                                                            " не теряй",
                random_id=random.randint(-1000000000, 1000000000)
            )
        else:
            vk.messages.send(
                user_id=user_id,
                message="Так, агент, давайте соблюдать субординацию, я не буду отвечать на это... если хочешь что-то "
                        "мне сказать, напиши 'помощь'",
                random_id=random.randint(-1000000000, 1000000000)
            )


def check_message_on_stage_one(cur_event):
    message = cur_event.text.lower()
    user_id = cur_event.user_id
    print(str(cur_event.user_id) + ": " + message)

    if message == "привет":
        vk.messages.send(
            user_id=user_id,
            message="Привет! Я твой куратор в этом состязании. Пиши сюда, все, что с ним связано. Так же напиши"
                    " 'помощь', если захочешь узнать, что мне можно сказать",
            random_id=random.randint(-1000000000, 1000000000)
        )
    elif message == "регистрация":
        vk.messages.send(
            user_id=user_id,
            message="Ты опоздал, состязание уже началось, в следующий раз не опаздывай",
            random_id=random.randint(-1000000000, 1000000000)
        )

    elif message == "помощь":
        vk.messages.send(
            user_id=user_id,
            message="убийство - если вы совершили убийство, пишите эту команду, а затем отправляете пароль",
            random_id=random.randint(-1000000000, 1000000000)
        )

    elif message == "убийство":
        vk.messages.send(
            user_id=user_id,
            message="Оу, отлично, давайте мне пароль, посмотрим...",
            random_id=random.randint(-1000000000, 1000000000)
        )
        set_user_state(user_id, "waiting_password")

    # Администратор пишет определенные буквы в определнном регистре
    elif cur_event.text == "СмеНА сТадИи " + config.passwd:
        set_game_stage(2)
        send_messages_to_all_users("Игра закончилась, ждите подсчета итогов!")

    else:
        if get_user_state(user_id) == "waiting_password":
            if check_kill(user_id, cur_event.text):
                new_target = change_victim(user_id)
                if check_alive() != 2:
                    image, group = generate_message_about_victim(new_target)
                    vk.messages.send(
                        user_id=user_id,
                        message="Отлично, вот твоя следующая цель:\n Группа:  " + group + "\n Фотография: ",
                        attachment=image,
                        random_id=random.randint(-1000000000, 1000000000)
                    )
                else:
                    send_messages_to_all_users("Внимание, осталось два охотника, состязание окончено")
                    set_game_stage(2)
            else:
                vk.messages.send(
                    user_id=user_id,
                    message="Слушай, не пвтайся меня обмануть, это либо не тот пароль, либо не твоя жертва...",
                    random_id=random.randint(-1000000000, 1000000000)
                )
            set_user_state(user_id, "")
        else:
            vk.messages.send(
                user_id=user_id,
                message="Так, агент, давайте соблюдать субординацию, я не буду отвечать на это... если хочешь что-то "
                        "мне сказать, напиши 'помощь'",
                random_id=random.randint(-1000000000, 1000000000)
            )


def check_message_on_stage_two(cur_event):
    vk.messages.send(
        user_id=cur_event.user_id,
        message="Ведется подсчет итогов. Ожидайте",
        random_id=random.randint(-1000000000, 1000000000)
    )


while True:
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            print("Check user")
            if get_user(event.user_id) is None:
                print("Add new user")
                register_new_user(event.user_id)
            game_stage = get_game_stage()
            if game_stage == 0:
                check_message_on_stage_zero(event)
            elif game_stage == 1:
                check_message_on_stage_one(event)
            elif game_stage == 2:
                check_message_on_stage_two(event)
