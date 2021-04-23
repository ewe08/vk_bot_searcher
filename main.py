import os
import sys
import json
import vk_api
import random
import requests
import wikipedia
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

# импорт всех личных данных
from info import *

wikipedia.set_lang('ru')

vk_session = vk_api.VkApi(
    token=TOKEN)
vk = vk_session.get_api()
vk_sess = vk_api.VkApi(
    token=user_token, scope=4)
_vk = vk_sess.get_api()
longpoll = VkBotLongPoll(vk_session, group_id)


def main():
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            try:
                photo = Photo(event)
                print(event.obj.message)
                text = event.obj.message["text"].strip(".,?!").lower()
                if text in ["игра"]:
                    Game(event)
                elif text in ["запомни"]:
                    photo.save_photo()
                elif text in ["список"]:
                    photo.photo_list()
                elif text in ["команды"]:
                    return_info(event)
                else:
                    output(event, 'вы ввели что-то непонятное...\n'
                                  'Вы можете ознакомиться с командами написав "команды"')
                output_info_user(event)
            except Exception as ex:
                output(event, ex)


def hello(event):
    response = vk.users.get(user_id=event.obj.message['from_id'], fields='city')
    name = response[0]["first_name"]
    output(event, f"Привет, {name}")
    if "city" in response[0]:
        output(event, f"Как поживает {response[0]['city']['title']}?")


def return_info(event):
    commands = "Игра - Вы запускаете географический тест \n " \
               "Запомни - Вы отправляете боту фотографию, а он ее " \
               "запоминает по тегу и может веруть в любой момент\n" \
               "Список - Выводит список всех этих фотографий"
    output(event, commands)


class Photo:
    def __init__(self, event):
        self.event = event
        self.user = str(event.obj.message["from_id"])
        self.tag = None
        self.url = None
        self.photos = os.listdir()

    def save_photo(self):
        output(self.event, "Отправте фотографию с подписью, которуе нужно запомнить.")
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                # Проверка, что есть фотография
                if not event.obj.message["attachments"]:
                    return
                self.event = event
                self.url = event.obj.message["attachments"][0]["photo"]["sizes"][-1]["url"]
                self.tag = event.obj.message["text"]
                img_data = requests.get(self.url).content
                try:
                    os.mkdir(f"data/{self.user}")
                except OSError:
                    pass
                with open(f'data/{self.user}/{self.tag}.jpg', 'wb') as handler:
                    handler.write(img_data)
                output(self.event, "Я запомнил эту фотографию.")
                break

    def photo_list(self):
        os.chdir(f'data/{self.user}')
        self.photos = os.listdir()
        os.chdir('../..')
        print(os.getcwd())
        output(self.event, "У меня сохранены фото:")
        i = 0
        for photo in self.photos:
            output(self.event, f"{i}: {photo}")
            i += 1
        output(self.event, "Какая нужна? (Указать номер)")
        self.get_photo()

    def get_photo(self):
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                index = event.obj.message["text"].strip(".,?!").lower()
                upload = vk_api.VkUpload(vk_session)
                output(event, "Вот ваша фотография")
                photo = [f"data/{self.user}/{self.photos[int(index)]}"]
                photo = upload.photo_messages(photo)
                print(photo)
                vk.messages.send(user_id=self.user,
                                 attachment='photo{}_{}'.format(photo[0]['owner_id'],
                                                                photo[0]['id']),
                                 random_id=random.randint(0, 2 ** 64))
                break


class Game:
    def __init__(self, event):
        self.event = event
        self.photo = random.choice(get_photo_from_album(group=group_id, album=city_album))
        with open('city.json') as js_f:
            data = dict(json.load(js_f))
        self.city = data[str(self.photo[1])].lower()
        self.play()

    def play(self):
        output(self.event, "Что это за город?")
        vk.messages.send(user_id=self.event.obj.message['from_id'],
                         attachment=self.photo[0],
                         random_id=random.randint(0, 2 ** 64))
        with open('city.json') as js_f:
            data = dict(json.load(js_f))
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                text = event.obj.message["text"].strip(".,?!").lower()
                if text == self.city:
                    output(event, "Правильно!")
                    break
                else:
                    output(event, f"Нет, это {data[str(self.photo[1])]}.")
                    break
        self.go_wiki()

    def go_wiki(self):
        output(self.event, "Хотите узнать больше про этот город?")
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                text = event.obj.message["text"].strip(".,?!").lower()
                if text == 'да':
                    self.search_wiki()
                else:
                    return

    def search_wiki(self):
        info = wikipedia.summary(self.city)
        output(self.event, info)


def output_info_user(event):
    print('Для меня от:', event.obj.message['from_id'])
    print('Текст:', event.obj.message['text'])
    print()


def output(event, text):
    vk.messages.send(user_id=event.obj.message['from_id'],
                     message=text,
                     random_id=random.randint(0, 2 ** 64))


def get_coord(address):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": address,
        "format": "json"}

    response = requests.get(geocoder_api_server, params=geocoder_params)
    if response:
        # Преобразуем ответ в json-объект
        json_response = response.json()

        toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_pos = str(toponym["Point"]["pos"]).replace(' ', ',')
        return toponym_pos


def get_image(coord):
    map_request = "http://static-maps.yandex.ru/1.x/"

    params = {
        "ll": coord,
        "z": 14,
        "l": 'sat'
    }
    response = requests.get(map_request, params=params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)

    # Запишем полученное изображение в файл.
    map_file = "map.png"
    with open(map_file, "wb") as file:
        file.write(response.content)
    return map_file


def get_photo_from_album(album, group):
    response = _vk.photos.get(album_id=album, group_id=group)
    photos_id = []
    for photo in response["items"]:
        photos_id.append((f'photo{photo["owner_id"]}_{photo["id"]}', photo["id"]))
    return photos_id


# Фунуция для обновления списка городов
def add_counties():
    countries = ['Новосибирск', 'Москва', 'Санкт-Петербург', 'Барнаул', 'Калининград',
                 'Казань', 'Томск', 'Выборг', 'Смоленск', 'Ростов-на-Дону']
    with open("city.json") as json_f:
        data = dict(json.load(json_f))
    for c in countries:
        coordinates = get_coord(c)
        map_file = get_image(coordinates)
        upload = vk_api.VkUpload(vk_sess)
        photo = upload.photo(map_file, group_id=group_id, album_id=city_album)
        key = photo[0]["id"]
        data[key] = c
        os.remove(map_file)
    with open("city.json", 'w') as json_f:
        json.dump(data, json_f)


if __name__ == '__main__':
    main()
