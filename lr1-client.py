import socket
import dearpygui.dearpygui as dpg
import screeninfo
import threading

# Получаем разрешение экрана
monitor = screeninfo.get_monitors()[0]
SCREEN_WIDTH, SCREEN_HEIGHT = monitor.width, monitor.height

# Размеры окна и элементов
WINDOW_WIDTH = int(SCREEN_WIDTH * 0.5)
WINDOW_HEIGHT = int(SCREEN_HEIGHT * 0.6)
INPUT_WIDTH = int(WINDOW_WIDTH * 0.67)  # 2/3 ширины окна
ERROR_BOX_HEIGHT = int(WINDOW_HEIGHT * 0.2)  # Ограничиваем высоту окна с ошибками

# Переменные
server_ip = "127.0.0.1"
server_port = "12345"
username = ""
password = ""
access_key = ""
error_logs = []
client_socket = None
connected = False
font_path = "NotoSans-Regular.ttf"


# Функции
def log_error(error_msg):
    """Добавляет сообщение об ошибке в лог."""
    error_logs.append(error_msg)
    update_error_log()


def clear_errors():
    """Очищает окно с ошибками."""
    error_logs.clear()
    update_error_log()


def update_error_log():
    """Обновляет отображение ошибок"""
    dpg.configure_item("error_log", default_value="\n".join(error_logs))


def validate_fields():
    """Проверяет, заполнены ли все поля."""
    global server_ip, server_port, username, password, access_key

    server_ip = dpg.get_value("server_ip").strip()
    server_port = dpg.get_value("server_port").strip()
    username = dpg.get_value("username").strip()
    password = dpg.get_value("password").strip()
    access_key = dpg.get_value("access_key").strip()

    if not server_ip:
        log_error("Поле 'IP сервера' не может быть пустым.")
        return False
    if not server_port:
        log_error("Поле 'Порт' не может быть пустым.")
        return False
    if not username:
        log_error("Поле 'Имя пользователя' не может быть пустым.")
        return False
    if not password:
        log_error("Поле 'Пароль' не может быть пустым.")
        return False
    if not access_key:
        log_error("Поле 'Ключ доступа' не может быть пустым.")
        return False
    if "." in username:
        log_error("Поле 'Имя пользователя' не может содержать точку.")
        return False
    if "." in password:
        log_error("Поле 'Пароль' не может содержать точку.")
        return False
    if "." in access_key:
        log_error("Поле 'Ключ доступа' не может содержать точку.")
        return False
    return True


def connect_to_server():
    """Подключается к серверу и выполняет аутентификацию."""
    global client_socket, connected

    if not validate_fields():
        return

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3)
        client_socket.connect((server_ip, int(server_port)))

        auth_data = f"{username}.{password}.{access_key}"
        client_socket.sendall(auth_data.encode("utf-8"))

        response = client_socket.recv(1024).decode("utf-8", errors="replace").strip()
        if response == "AUTH_SUCCESS":
            log_error("Подключение успешно!")
            connected = True
            dpg.configure_item("connect_window", show=False)
            dpg.configure_item("chat_window", show=True)

            # Запускаем поток для прослушивания сервера
            threading.Thread(target=listen_to_server, daemon=True).start()
        else:
            log_error("Аутентификация не удалась.")
            client_socket.close()
            client_socket = None
    except socket.error as e:
        log_error(f"Ошибка подключения: {str(e)}")
        client_socket = None


manual_disconnect = False  # Флаг, разорвал ли соединение сам клиент


def listen_to_server():
    """Прослушивает соединение и отслеживает разрыв."""
    global connected, client_socket, manual_disconnect
    try:
        client_socket.settimeout(None)  # Отключаем таймаут для постоянного прослушивания
        while connected:
            data = client_socket.recv(1024)
            if not data:
                break  # Сервер закрыл соединение
    except (socket.error, ConnectionResetError):
        pass  # Игнорируем временные сбои

    if not manual_disconnect:
        log_error("Соединение разорвано сервером.")
    else:
        log_error("Вы отключились от сервера.")  # Сообщение при ручном отключении
    disconnect()


def disconnect():
    """Разрывает соединение с сервером."""
    global connected, client_socket, manual_disconnect
    if connected:
        manual_disconnect = True
        connected = False
        if client_socket:
            client_socket.close()
            client_socket = None
        dpg.configure_item("chat_window", show=False)
        dpg.configure_item("connect_window", show=True)
    manual_disconnect = False  # Сбрасываем флаг


def send_message():
    """Отправляет сообщение на сервер."""
    global client_socket

    if connected and client_socket:
        try:
            message = dpg.get_value("message")
            if message:
                client_socket.sendall(message.encode("utf-8"))
                dpg.set_value("message", "")
        except socket.error:
            log_error("Не удалось отправить сообщение.")


def exit_application():
    """Закрывает приложение."""
    disconnect()
    dpg.stop_dearpygui()


# Интерфейс
dpg.create_context()

# Добавляем шрифт с поддержкой кириллицы
with dpg.font_registry():
    with dpg.font(font_path, 20) as font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
        dpg.bind_font(font)

# Основное окно подключения
with dpg.window(label="Подключение к серверу", tag="connect_window", width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
    dpg.add_input_text(label="IP сервера", tag="server_ip", default_value=server_ip, width=INPUT_WIDTH)
    dpg.add_input_text(label="Порт", tag="server_port", default_value=server_port, width=INPUT_WIDTH)
    dpg.add_input_text(label="Имя пользователя", tag="username", default_value=username, width=INPUT_WIDTH)
    dpg.add_input_text(label="Пароль", tag="password", default_value=password, password=True, width=INPUT_WIDTH)
    dpg.add_input_text(label="Ключ доступа", tag="access_key", default_value=access_key, width=INPUT_WIDTH)

    # Кнопки в одной строке
    with dpg.group(horizontal=True):
        dpg.add_button(label="Подключиться", callback=connect_to_server)
        dpg.add_button(label="Очистить ошибки", callback=clear_errors)
        dpg.add_button(label="Выход", callback=exit_application)

    dpg.add_text("Ошибки:")
    dpg.add_text("", tag="error_log", wrap=0)  # Включает автоматический перенос строк

# Окно чата
with dpg.window(label="Чат с сервером", tag="chat_window", width=WINDOW_WIDTH, height=WINDOW_HEIGHT, show=False):
    dpg.add_input_text(label="Сообщение", tag="message", width=INPUT_WIDTH)

    with dpg.group(horizontal=True):
        dpg.add_button(label="Отправить", callback=send_message)
        dpg.add_button(label="Разорвать соединение", callback=disconnect)

# Запуск интерфейса
dpg.create_viewport(title="TCP/IP Client", width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("connect_window", True)
dpg.start_dearpygui()
dpg.destroy_context()
