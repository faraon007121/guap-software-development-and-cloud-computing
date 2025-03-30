import os
import sys
import traceback
from fileinput import filename
from ftplib import FTP, error_perm
from pathlib import Path

import dearpygui.dearpygui as dpg

ftp = None  # Глобальная переменная для FTP соединения
error_messages = []  # Список для хранения сообщений об ошибках
current_path = ""  # Текущий каталог на сервере
font_path = "NotoSans-Regular.ttf"
server_encoding = "utf-8"
client_encoding = None

if client_encoding is None:
    client_encoding = "cp1251" if sys.platform.startswith("win") else "utf-8"


def update_error_log(message):
    global error_messages
    error_messages.append(message)
    log_text = "\n".join(error_messages)
    dpg.set_value("error_log", log_text)
    dpg.set_value("error_log_auth", log_text)
    dpg.set_value("error_log_files", log_text)
    print(message)


def connect_ftp():
    global ftp
    dpg.configure_item("connect_button", enabled=False)
    ip = dpg.get_value("ip_input")

    if not validate_ip(ip):
        update_error_log("Ошибка: IP-адрес или домен не может быть пустым")
        dpg.configure_item("connect_button", enabled=True)
        return

    try:
        ftp = FTP(ip)
        ftp.encoding = server_encoding
        ftp.connect()
        update_error_log("Соединение установлено")
        dpg.configure_item("window_1", show=False)
        dpg.configure_item("window_2", show=True)
    except Exception as e:
        update_error_log(f"Ошибка подключения: {e}")
    dpg.configure_item("connect_button", enabled=True)


def exit_app():
    dpg.stop_dearpygui()


def validate_ip(ip):
    return bool(ip.strip())


def validate_credentials(value):
    return bool(value.strip())


def login_ftp():
    global ftp, current_path
    dpg.configure_item("login_button", enabled=False)
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    if not validate_credentials(username) or not validate_credentials(password):
        update_error_log("Ошибка: Логин и пароль не могут быть пустыми")
        dpg.configure_item("login_button", enabled=True)
        return

    try:
        ftp.login(username, password)
        current_path = ftp.pwd()
        update_error_log("Авторизация успешна")
        print(ftp.sendcmd("OPTS UTF8 ON"))
        dpg.configure_item("window_2", show=False)
        dpg.configure_item("window_3", show=True)
        list_files()
    except error_perm as e:
        update_error_log(f"Ошибка авторизации: {e}")
    except EOFError:
        update_error_log("Ошибка соединения. Попробуйте переподключиться.")
        disconnect_ftp()
    dpg.configure_item("login_button", enabled=True)


def disconnect_ftp():
    global ftp
    if ftp:
        ftp.quit()
        ftp = None
        update_error_log("Соединение разорвано")
    dpg.configure_item("window_2", show=False)
    dpg.configure_item("window_3", show=False)
    dpg.configure_item("window_1", show=True)


def create_directories():
    try:
        root_folder = "Z3440MK_ЛакиревАЕ"
        encoded_folder_name = root_folder.encode(server_encoding).decode(client_encoding)
        ftp.mkd(encoded_folder_name)
        for i in range(10):
            subfolder = f"{encoded_folder_name}/{i}"
            ftp.mkd(subfolder)
            for j in range(10):
                ftp.mkd(f"{subfolder}/{j}")
        update_error_log("Каталоги успешно созданы")
    except error_perm as e:
        update_error_log(f"Ошибка создания каталогов: {e}")
    list_files()


def list_files():
    global current_path
    try:
        update_error_log(f"Запрашиваем файлы в каталоге: {current_path}")
        file_list = []
        ftp.dir(file_list.append)  # Аналог retrlines, но можно модифицировать обработку
        files = []
        for entry in file_list:
            parts = entry.split()
            files.append(" ".join(parts[8:]))

        decoded_files = {}  # Храним {отображаемое имя: оригинальное имя}

        for file in files:
            try:
                # Декодируем в удобочитаемый вид, но сохраняем оригинальное имя
                display_name = file.encode(client_encoding).decode(server_encoding)
                decoded_files[display_name] = file  # Сохраняем соответствие
            except UnicodeDecodeError as e:
                problem_bytes = file.encode(client_encoding)
                error_position = e.start
                byte_context = problem_bytes[max(0, error_position - 5): error_position + 5]
                update_error_log(f"Ошибка декодирования UTF-8 в файле: {file}| Проблемные байты: {byte_context}")
                decoded_files[file] = file  # Сохраняем оригинальное имя как fallback

        # Обновляем listbox, передавая user_data (исходное имя файла)
        dpg.configure_item("file_list", items=list(decoded_files.keys()))
        dpg.set_item_user_data("file_list", decoded_files)  # Храним mapping

        print(f"Список файлов в client кодировке: {list(decoded_files.keys())}")
        print(f"Список файлов в server кодировке: {list(decoded_files.values())}")

    except Exception as e:
        traceback.print_exc()
        update_error_log(f"Ошибка получения списка файлов: {e}")


def change_directory(sender, app_data, user_data):
    global current_path
    try:
        # Получаем оригинальное имя файла из user_data
        original_name = dpg.get_item_user_data("file_list").get(app_data, app_data)

        update_error_log(f"Переход в каталог: {original_name}")
        ftp.cwd(original_name)  # Используем оригинальное имя
        current_path = ftp.pwd()
        list_files()
    except Exception as e:
        update_error_log(f"Ошибка смены каталога: {e}")
        traceback.print_exc()


def go_back():
    global current_path
    try:
        update_error_log("Возврат на уровень выше")
        ftp.cwd("..")
        current_path = ftp.pwd()
        list_files()
    except Exception as e:
        update_error_log(f"Ошибка при возврате назад: {e}")


def delete_directory_recursive(path):
    try:
        base_name = os.path.basename(path.rstrip('/'))
        if base_name in [".", ".."]:
            return
        ftp.cwd(path)
        items = []
        ftp.retrlines('LIST', items.append)
        for item in items:
            parts = item.split()
            name = " ".join(parts[8:])
            if item.startswith('d'):
                delete_directory_recursive(f"{path}/{name}")
            else:
                ftp.delete(f"{path}/{name}")
        ftp.cwd("..")
        ftp.rmd(path)
        update_error_log(f"Директория удалена: {path}")
    except error_perm as e:
        update_error_log(f"Ошибка при удалении: {e}")
    except Exception as e:
        update_error_log(f"Ошибка при удалении директории: {e}")


def on_delete_directory():
    folder = dpg.get_value("delete_input")
    if not folder.strip():
        update_error_log("Ошибка: имя директории не может быть пустым")
        return
    try:
        delete_directory_recursive(folder)
        dpg.set_value("delete_input", "")
        list_files()
    except error_perm as e:
        update_error_log(f"Ошибка: директория не найдена: {e}")


def on_file_select(sender, app_data, user_data):
    dpg.set_item_user_data("context_delete_button", app_data)
    change_directory(sender, app_data, user_data)


def delete_file(path):
    try:
        ftp.delete(path)
        update_error_log(f"Файл удалён: {path}")
    except error_perm as e:
        update_error_log(f"Ошибка при удалении файла: {e}")
    except Exception as e:
        update_error_log(f"Ошибка при удалении файла: {e}")


def on_context_delete():
    selected = dpg.get_value("file_list")
    selected = dpg.get_item_user_data("file_list").get(selected, selected)
    remote_path = os.path.join(current_path, selected).replace("\\", "/")
    if not remote_path:
        update_error_log("Ошибка: путь не может быть пустым")
        return

    try:
        # Проверка типа (директория или файл)
        current = ftp.pwd()
        try:
            ftp.cwd(remote_path)
            # Успешно перешли — это директория
            ftp.cwd(current)  # вернуться обратно
            delete_directory_recursive(remote_path)
        except error_perm:
            # Не директория — пробуем удалить как файл
            delete_file(remote_path)

        list_files()
    except Exception as e:
        update_error_log(f"Ошибка при удалении: {e}")
    dpg.configure_item("context_menu", show=False)


def show_context_menu(sender, app_data, user_data):
    dpg.set_value("context_target_file", app_data)
    dpg.show_item("context_menu")


def download_file(file_name, local_path):
    if filename in [".", ".."]:
        update_error_log(f"Некорректное имя файла для скачивания: {filename}")
        return
    try:
        with open(local_path, 'wb') as local_file:
            ftp.retrbinary(f"RETR {file_name}", local_file.write)
        update_error_log(f"Файл {file_name} скачан успешно в {local_path}")
    except Exception as e:
        update_error_log(f"Ошибка при скачивании файла {file_name}: {e}")


# Функция для скачивания каталога рекурсивно
def download_directory(directory_name, local_path):
    try:
        directory_file_name = os.path.basename(directory_name.rstrip('/'))
        directory_file_name = next(
            (k for k, v in dpg.get_item_user_data("file_list").items() if v == directory_file_name),
            directory_file_name)
        local_path = os.path.join(local_path, directory_file_name)
        os.makedirs(local_path, exist_ok=True)
        items = []
        ftp.retrlines(f"LIST {directory_name}", items.append)

        for item in items:
            parts = item.split()
            name = " ".join(parts[8:])
            if name in [".", ".."]:
                continue
            if item.startswith('d'):  # Если это директория
                download_directory(f"{directory_name}/{name}", local_path)
            else:  # Если это файл
                download_file(f"{directory_name}/{name}", os.path.join(local_path, name))
        update_error_log(f"Каталог {directory_name} скачан успешно в {local_path}")
    except Exception as e:
        update_error_log(f"Ошибка при скачивании каталога {directory_name}: {e}")


# Функция обработки скачивания по контекстному меню
def on_context_download(sender, app_data, user_data):
    selected = dpg.get_value("file_list")
    selected = dpg.get_item_user_data("file_list").get(selected, selected)
    if selected:
        # Указание пути на локальную машину
        local_path = dpg.get_value("download_path_input")  # Поле для ввода пути загрузки
        if not local_path.strip():
            update_error_log("Ошибка: путь для скачивания не указан")
            return

        try:
            remote_path = os.path.join(current_path, selected).replace("\\", "/")
            original_path = ftp.pwd()

            try:
                # Пробуем перейти в директорию — если получилось, значит это папка
                ftp.cwd(remote_path)
                is_directory = True
                ftp.cwd(original_path)  # Возвращаемся обратно
            except Exception:
                is_directory = False

            if is_directory:
                download_directory(remote_path, local_path)
            else:
                download_file(remote_path, os.path.join(local_path, selected))

            list_files()  # Обновить список файлов после скачивания
        except Exception as e:
            update_error_log(f"Ошибка скачивания: {e}")
    dpg.configure_item("context_menu", show=False)


def get_default_download_path():
    if sys.platform == "win32":  # Для Windows
        # Путь к папке "Загрузки" на Windows
        return str(Path(os.environ.get("USERPROFILE", "")).joinpath("Downloads"))
    elif sys.platform == "darwin":  # Для macOS
        # Путь к папке "Загрузки" на macOS
        return str(Path(os.environ.get("HOME", "")).joinpath("Downloads"))
    else:
        # Для других ОС (например, Linux)
        return str(Path(os.environ.get("HOME", "")).joinpath("Downloads"))


def change_directory_popup(sender, app_data, user_data):
    global current_path
    selected = dpg.get_value("file_list")
    selected = dpg.get_item_user_data("file_list").get(selected, selected)
    if selected:
        path = os.path.join(current_path, selected).replace("\\", "/")
        try:
            ftp.cwd(path)
            current_path = ftp.pwd()
            update_error_log(f"Переход в каталог: {path}")
            list_files()
        except Exception as e:
            update_error_log(f"Ошибка при переходе в каталог: {e}")
    dpg.configure_item("context_menu", show=False)


def upload_file():
    local_file = dpg.get_value("upload_local_file")

    if not os.path.isfile(local_file):
        update_error_log(f"Ошибка: файл не найден или это директория: {local_file}")
        return

    name = os.path.basename(local_file)

    try:
        # Переход в целевую директорию на сервере
        ftp.cwd(current_path)

        with open(local_file, "rb") as f:
            ftp.storbinary(f"STOR {name}", f)

        update_error_log(f"Файл успешно загружен в {current_path}/{name}")
        list_files()
    except Exception as e:
        update_error_log(f"Ошибка загрузки файла: {e}")
    list_files()


default_download_path = get_default_download_path()
print(f'Default download path: {default_download_path}')
dpg.create_context()

with dpg.font_registry():
    with dpg.font(font_path, 20) as font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
        dpg.bind_font(font)

with dpg.window(label="FTP Подключение", tag="window_1", width=1280, height=720):
    dpg.add_input_text(label="IP-адрес", tag="ip_input", default_value="ftp.spectec.ru")
    dpg.add_button(label="Подключиться", tag="connect_button", callback=connect_ftp)
    dpg.add_button(label="Выйти", callback=exit_app)
    with dpg.child_window(height=200):
        dpg.add_text("", tag="error_log", wrap=400)

with dpg.window(label="FTP Авторизация", tag="window_2", show=False, width=1280, height=720):
    dpg.add_input_text(tag="context_target_file", show=False)
    dpg.add_input_text(label="Логин", tag="username_input", default_value="tempftp")
    dpg.add_input_text(label="Пароль", tag="password_input", password=True)
    dpg.add_button(label="Авторизоваться", tag="login_button", callback=login_ftp)
    dpg.add_button(label="Назад", callback=disconnect_ftp)
    with dpg.child_window(height=200):
        dpg.add_text("", tag="error_log_auth", wrap=400)

with dpg.window(label="FTP Файлы", tag="window_3", show=False, width=1280, height=720):
    dpg.add_button(label="Создать каталоги", callback=create_directories)
    dpg.add_button(label="Отключиться", callback=disconnect_ftp)
    dpg.add_button(label="Назад", callback=go_back)
    dpg.add_input_text(label="Путь для скачивания", tag="download_path_input", default_value=default_download_path)
    dpg.add_input_text(label="Имя файла для загрузки", tag="upload_local_file", default_value=default_download_path)
    dpg.add_button(label="Загрузить файл в текущую директорию", callback=upload_file)
    file_container = dpg.add_group(tag="file_list_container", label="Файлы")
    dpg.add_listbox([], tag="file_list", callback=None, num_items=12, parent=file_container)
    with dpg.popup(parent="file_list", tag="context_menu", mousebutton=dpg.mvMouseButton_Right):
        dpg.add_button(label="Перейти в каталог", callback=change_directory_popup)
        dpg.add_button(label="Скачать", callback=on_context_download)
        dpg.add_button(label="Удалить", callback=on_context_delete)
        dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("context_menu", show=False))
    with dpg.child_window(height=200):
        dpg.add_text("", tag="error_log_files", wrap=400)

dpg.create_viewport(title="FTP Client", width=1280, height=720)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
