import ftplib

import dearpygui.dearpygui as dpg
from ftplib import FTP, error_perm, error_temp, error_proto, error_reply
import os

ftp = None  # Глобальная переменная для FTP соединения
error_messages = []  # Список для хранения сообщений об ошибках
current_path = ""  # Текущий каталог на сервере

font_path = "NotoSans-Regular.ttf"


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
        ftp.encoding = "latin1"  # Пробуем установить кодировку по умолчанию
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
        ftp.mkd(root_folder)
        for i in range(10):
            subfolder = f"{root_folder}/{i}"
            ftp.mkd(subfolder)
            for j in range(10):
                ftp.mkd(f"{subfolder}/{j}")
        update_error_log("Каталоги успешно созданы")
    except error_perm as e:
        update_error_log(f"Ошибка создания каталогов: {e}")


def list_files():
    global current_path
    try:
        update_error_log(f"Запрашиваем файлы в каталоге: {current_path}")
        raw_files = []
        ftp.retrlines('LIST', raw_files.append)  # Получаем список файлов в raw формате
        files = [line.split()[-1] for line in raw_files]  # Парсим имена файлов
        decoded_files = []

        for file in files:
            try:
                decoded_files.append(file.encode('latin1').decode('utf-8'))
            except UnicodeDecodeError as e:
                problem_bytes = file.encode('latin1')
                error_position = e.start
                byte_context = problem_bytes[max(0, error_position - 5): error_position + 5]
                update_error_log(f"Ошибка декодирования UTF-8 в файле: {file}. Проблемные байты: {byte_context}")
                try:
                    decoded_files.append(file.encode('latin1').decode('cp1251'))
                except UnicodeDecodeError:
                    decoded_files.append(file)  # Оставляем оригинальное имя, если декодирование не удалось
        dpg.configure_item("file_list", items=decoded_files)
        update_error_log(f"Список файлов: {decoded_files}")
    except Exception as e:
        print(e.__class__)
        update_error_log(f"Ошибка получения списка файлов: {e}")


def change_directory(sender, app_data, user_data):
    print(user_data)
    global current_path
    try:
        update_error_log(f"Переход в каталог: {user_data}")
        ftp.cwd(user_data)
        current_path = ftp.pwd()
        list_files()
    except Exception as e:
        update_error_log(f"Ошибка смены каталога: {e}")


def go_back():
    global current_path
    try:
        update_error_log("Возврат на уровень выше")
        ftp.cwd("..")
        current_path = ftp.pwd()
        list_files()
    except Exception as e:
        update_error_log(f"Ошибка при возврате назад: {e}")


dpg.create_context()

with dpg.font_registry():
    with dpg.font(font_path, 20) as font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
        dpg.bind_font(font)

with dpg.window(label="FTP Подключение", tag="window_1", width=400, height=300):
    dpg.add_input_text(label="IP-адрес", tag="ip_input", default_value="ftp.spectec.ru")
    dpg.add_button(label="Подключиться", tag="connect_button", callback=connect_ftp)
    dpg.add_button(label="Выйти", callback=exit_app)
    with dpg.child_window(height=100):
        dpg.add_text("", tag="error_log", wrap=400)

with dpg.window(label="FTP Авторизация", tag="window_2", show=False, width=400, height=300):
    dpg.add_input_text(label="Логин", tag="username_input", default_value="tempftp")
    dpg.add_input_text(label="Пароль", tag="password_input", password=True)
    dpg.add_button(label="Авторизоваться", tag="login_button", callback=login_ftp)
    dpg.add_button(label="Назад", callback=disconnect_ftp)
    with dpg.child_window(height=100):
        dpg.add_text("", tag="error_log_auth", wrap=400)

with dpg.window(label="FTP Файлы", tag="window_3", show=False, width=500, height=400):
    dpg.add_button(label="Создать каталоги", callback=create_directories)
    dpg.add_button(label="Отключиться", callback=disconnect_ftp)
    dpg.add_button(label="Назад", callback=go_back)
    dpg.add_listbox([], tag="file_list", callback=change_directory)
    with dpg.child_window(height=100):
        dpg.add_text("", tag="error_log_files", wrap=500)

dpg.create_viewport(title="FTP Client", width=600, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()