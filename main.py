import time
import traceback
import vk_api
import random
import config
import sqlite3
import string
import face_detect

from vk_api.longpoll import VkLongPoll, VkEventType


def connect_to_vk():
    print("Connecting to VK")
    global vk_session
    global longpoll
    global vk

    vk_session = vk_api.VkApi(token=config.token)

    longpoll = VkLongPoll(vk_session)

    vk = vk_session.get_api()

    print("Successfully connected to VK")


connect_to_vk()

conn = sqlite3.connect(config.sqlite_path)
c = conn.cursor()
print("Successfully connected to DB")
print("Server successfully started")
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
    cmd = "INSERT INTO user_info(user_id, user_password, is_dead, is_registered, is_aproved)" \
          " VALUES (%d, '%s', 0, 0, -1)" % (user_id, generate_user_password())
    c.execute(cmd)
    conn.commit()


def get_unaproved_user():
    cmd = "SELECT user_id FROM user_info WHERE is_aproved=0"
    c.execute(cmd)
    result = c.fetchone()
    if result is not None:
        return result[0]
    else:
        return None


def set_aprove_state(user_id, state):
    cmd = "UPDATE user_info SET is_aproved=%d WHERE user_id=%d" % (state, user_id)
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


def get_image_from_dialogue(cur_event, what_to_get = 0):
    result = vk_session.method("messages.getById", {
        "message_ids": [cur_event.message_id],
        "group_id": config.group_id
    })
    print(result)
    try:
        photo = result['items'][0]['attachments'][0]['photo']
        if what_to_get == 0:
            return "photo{}_{}_{}".format(photo['owner_id'], photo['id'], photo['access_key'])
        elif what_to_get == 1:
            return result['items'][0]['attachments'][0]['photo']['sizes'][-1]['url']
    except:
        return None


def send_messages_to_all_users(message):
    cmd = "SELECT user_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        try:
            vk.messages.send(
                user_id=item[0],
                message=message,
                random_id=random.randint(-1000000000, 1000000000)
            )
        except Exception as e:
            print('Ошибка:\n', traceback.format_exc())
            print("User is banned")


def send_messages_about_victim_to_all_users():
    cmd = "SELECT user_id, target_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        image, group = generate_message_about_victim(item[1])
        message = "Ваша цель:\nСсылка на страничку: https://vk.com/id" + str(item[1]) + " \nГруппа:" + group + "\n Фотография: "
        try:
            vk.messages.send(
                user_id=item[0],
                message=message,
                attachment=image,
                random_id=random.randint(-1000000000, 1000000000)
            )
        except Exception as e:
            print('Ошибка:\n', traceback.format_exc())
            print("User is banned")


def generate_list_of_random_players(players):
    l = []
    for i in range(len(players)):
        object_to_interact = players[random.randint(0, len(players) - 1)]
        l.append(object_to_interact)
        players.remove(object_to_interact)

    return l


def generate_victims():
    cmd = "SELECT user_id FROM user_info WHERE is_registered = 1"
    c.execute(cmd)
    result = c.fetchall()
    list_of_players = generate_list_of_random_players(result)
    for item in list_of_players:
        cmd = "UPDATE user_info SET target_id = %d WHERE user_id = %d" %\
              (list_of_players[(list_of_players.index(item) + 1) % len(list_of_players)][0], item[0])
        c.execute(cmd)
        conn.commit()


def check_kill(user_id, message):
    cmd = "SELECT target_id FROM user_info WHERE user_id = %d" % user_id
    c.execute(cmd)
    cmd = "SELECT user_password FROM user_info WHERE user_id = %d" % c.fetchone()[0]
    c.execute(cmd)
    result = c.fetchone()[0]
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

    vk.messages.send(
        user_id=victim_id,
        message="Вы были убиты! Не расстраивайтесь, в следующий раз повезет",
        keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
        random_id=random.randint(-1000000000, 1000000000)
    )

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


def delete_all_unaproved_users():
    cmd = "SELECT user_id FROM user_info WHERE is_aproved = 0"
    c.execute(cmd)
    result = c.fetchall()
    for item in result:
        delete_user(item[0])


def delete_user(user_id):
    cmd = "DELETE FROM user_info WHERE user_id = %d" %user_id
    c.execute(cmd)
    conn.commit()
    cmd = "DELETE FROM users WHERE user_id = %d" % user_id
    c.execute(cmd)
    conn.commit()


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
            keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )
    elif message == "регистрация":
        if get_user_registration_status(user_id) == 0:
            vk.messages.send(
                user_id=user_id,
                message="Отлично! Теперь отправьте мне фотографию себя, чтобы другие охотники смогли вас найти",
                keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )
            set_user_state(user_id, "registration_image")
        else:
            vk.messages.send(
                user_id=user_id,
                message="Ты уже участвешь, жди начала...",
                keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )
    elif message == "проверка":
        if user_id in config.admin_list:
            user = get_unaproved_user()
            if user is not None:
                image, group = generate_message_about_victim(user)
                vk.messages.send(
                    user_id=user_id,
                    message="Вот пользователь на проверку:\n Ссылка на страничку: https://vk.com/id"
                                    + str(user) + " \nГруппа:  " + group + "\n Фотография: ",
                    attachment=image,
                    random_id=random.randint(-1000000000, 1000000000)
                )
                set_aprove_state(user, -2)
                set_user_state(user_id, "aproving " + str(user))
            else:
                vk.messages.send(
                    user_id=user_id,
                    message="Не осталось не подтвержденных пользователей",
                    keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
    # Администратор пишет определенные буквы в определнном регистре
    elif cur_event.text == "СмеНА сТадИи " + config.passwd:
        set_game_stage(1)
        send_messages_to_all_users("Внимание, игра началась!")
        generate_victims()
        send_messages_about_victim_to_all_users()
        delete_all_unaproved_users()

    elif message == "отмена":
        state = get_user_state(user_id)
        if state == "registration_image" or state == "registration_group":
            delete_user(user_id)
            vk.messages.send(
                user_id=user_id,
                message="Ну... не хочешь, как хочешь...",
                keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )
        else:
            vk.messages.send(
                user_id=user_id,
                message="Тебе нечего отменять",
                keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )
    else:
        user_state = get_user_state(user_id)
        if user_state == "registration_image":
            dialogue_image = get_image_from_dialogue(cur_event)
            dialogue_image_path = get_image_from_dialogue(cur_event, 1)
            print(dialogue_image_path)
            if dialogue_image is None:
                vk.messages.send(
                    user_id=user_id,
                    message="Слушай, тут нет фотографии, давай не пытаться обмануть друг-друга",
                    keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
            else:
                faces = face_detect.check_img(dialogue_image_path)
                if faces == 1:
                    set_user_image(user_id, dialogue_image)
                    set_user_state(user_id, "registration_group")
                    vk.messages.send(
                        user_id=user_id,
                        message="Укажите группу в которой вы учитесь (Например: 3ПКС-17-1к) или, если вы преподаватель,"
                                " укажите, что вы преподаете",
                        keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
                        random_id=random.randint(-1000000000, 1000000000)
                    )
                elif faces == 0:
                    vk.messages.send(
                        user_id=user_id,
                        message="На этой фотографии не видно или нет лица, отправь нормальную фотографию, я не могу"
                                "вклеивать в твое дело все что попало",
                        keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
                        random_id=random.randint(-1000000000, 1000000000)
                    )
                elif faces > 1:
                    vk.messages.send(
                        user_id=user_id,
                        message="Ты не один на фотографии, ножно чтобы ты был один",
                        keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
                        random_id=random.randint(-1000000000, 1000000000)
                    )
        elif user_state == "registration_group":
            set_user_group(user_id, event.text)
            set_user_state(user_id, "")
            set_user_registration_status(user_id)
            set_aprove_state(user_id, 0)
            vk.messages.send(
                user_id=user_id,
                message="Все, ты в игре, жди начала... Ах да, твой пароль: " + get_user_password(user_id) + ","
                                                                                                            " не теряй",
                keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )
        elif "aproving " in user_state:
            messages = message.split()
            modering_user_id = user_state.split()[1]
            if messages[0] == "удалить":
                vk.messages.send(
                    user_id=int(modering_user_id),
                    message="Внимание! Ваш аккаунт был не подтвержден администратором https://vk.com/id" + str(user_id)
                            + " по причине: " + message.replace("удалить ", "") + ". Зарегистрируйтесь заново, учтя все ошибки!",
                    keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
                delete_user(int(modering_user_id))
                vk.messages.send(
                    user_id=user_id,
                    message="Аккаунт пользователя https://vk.com/id"
                            + modering_user_id + " успешно удален по причине: " + message.replace("удалить ", ""),
                    keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
            elif messages[0] == "подтвердить":
                vk.messages.send(
                    user_id=int(modering_user_id),
                    message="Внимание! Ваш аккаунт был подтвержден администратором https://vk.com/id" + str(user_id)
                            + " ! Удачной игры!",
                    keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
                set_aprove_state(int(modering_user_id), 1)
                vk.messages.send(
                    user_id=user_id,
                    message="Аккаунт пользователя https://vk.com/id"
                            + modering_user_id + " успешно подтвержден",
                    keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
            else:
                vk.messages.send(
                    user_id=user_id,
                    message="Пожалуйста, укажите команду правильно: либо 'подтвердить', либо 'удалить причина'",
                    random_id=random.randint(-1000000000, 1000000000)
                )
        else:
            vk.messages.send(
                user_id=user_id,
                message="Так, агент, давайте соблюдать субординацию, я вас не понял, если ты хочешь попасть на "
                        "состязание, напиши команду 'Регистрация'",
                keyboard=open("stage_1.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )


def check_message_on_stage_one(cur_event):
    message = cur_event.text.lower()
    user_id = cur_event.user_id
    print(str(cur_event.user_id) + ": " + message)
    if get_user_registration_status(user_id) != 1:
        vk.messages.send(
            user_id=user_id,
            message="Ты опоздал, состязание уже началось, регистрация закончена, в следующий раз не опаздывай",
            random_id=random.randint(-1000000000, 1000000000)
        )
        return

    if message == "привет":
        vk.messages.send(
            user_id=user_id,
            message="Привет! Я твой куратор в этом состязании. Пиши сюда, все, что с ним связано. Так же напиши"
                    " 'помощь', если захочешь узнать, что мне можно сказать",
            keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )

    elif message == "помощь":
        vk.messages.send(
            user_id=user_id,
            message="убийство - если вы совершили убийство, пишите эту команду, а затем отправляете пароль",
            keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )

    elif message == "убийство":
        vk.messages.send(
            user_id=user_id,
            message="Оу, отлично, давайте мне пароль, посмотрим...",
            keyboard=open("cancel.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )
        set_user_state(user_id, "waiting_password")

    elif message == "отмена":
        set_user_state(user_id, "")
        vk.messages.send(
            user_id=user_id,
            message="Ну зачем тогда меня от дел?",
            keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )

    elif message == "мой пароль":
        vk.messages.send(
            user_id=user_id,
            message="Ну я же говорил, не теряй... ладно вот твой пароль " + get_user_password(user_id),
            keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
            random_id=random.randint(-1000000000, 1000000000)
        )
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
                        message="Отлично, вот твоя следующая цель:\n Ссылка на страничку: https://vk.com/id"
                                + str(new_target) + " \nГруппа:  " + group + "\n Фотография: ",
                        attachment=image,
                        keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
                        random_id=random.randint(-1000000000, 1000000000)
                    )
                else:
                    send_messages_to_all_users("Внимание, осталось два охотника, состязание окончено")
                    set_game_stage(2)
            else:
                vk.messages.send(
                    user_id=user_id,
                    message="Слушай, не пвтайся меня обмануть, это либо не тот пароль, либо не твоя жертва...",
                    keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
                    random_id=random.randint(-1000000000, 1000000000)
                )
            set_user_state(user_id, "")
        else:
            vk.messages.send(
                user_id=user_id,
                message="Так, агент, давайте соблюдать субординацию, я не буду отвечать на это... если хочешь что-то "
                        "мне сказать, напиши 'помощь'",
                keyboard=open("stage_2.json", "r", encoding="UTF-8").read(),
                random_id=random.randint(-1000000000, 1000000000)
            )


def check_message_on_stage_two(cur_event):
    vk.messages.send(
        user_id=cur_event.user_id,
        message="Ведется подсчет итогов. Ожидайте",
        random_id=random.randint(-1000000000, 1000000000)
    )


while True:
    try:
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
    except Exception as e:
        print('Ошибка:\n', traceback.format_exc())
        print("Я попытался упасть, но трай меня спас")
        time.sleep(5)
        print("Спас же?")
        connect_to_vk()
        print("Спааааас")
