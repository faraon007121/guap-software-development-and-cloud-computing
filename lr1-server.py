import socket
import threading
import hashlib
import dearpygui.dearpygui as dpg


USERNAME = "ЛакиревАндрейЕвгеньевич_Z3440MK"
STORED_PASSWORD_HASH = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"

# Глобальные переменные
server_socket = None
connections = []
messages = []
authenticated_clients = {}
server_running = False
port = 12345  # Порт по умолчанию
font_path = "NotoSans-Regular.ttf"


def username_hash(s: str) -> int:
    """Возвращает сумму ASCII-кодов первых трех символов имени пользователя."""
    return sum(ord(c) for c in s[:3])


# Функция для обновления логов в интерфейсе
def update_logs():
    dpg.set_value("log_messages", "\n".join(messages[-15:]))


# Запуск сервера
def start_server():
    global server_socket, server_running, port
    if server_running:
        messages.append("[WARNING] Сервер уже запущен.")
        update_logs()
        return

    try:
        port = int(dpg.get_value("port_input"))  # Читаем значение порта из GUI
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(5)
        server_running = True
        messages.append(f"[INFO] Сервер запущен на порту {port}")
        update_logs()
        threading.Thread(target=accept_connections, daemon=True).start()
    except Exception as e:
        messages.append(f"[ERROR] Ошибка запуска сервера: {str(e)}")
        update_logs()


# Остановка сервера
def stop_server():
    global server_running, server_socket
    if not server_running:
        messages.append("[WARNING] Сервер не запущен.")
        update_logs()
        return

    server_running = False
    for sock, _ in connections:
        sock.close()
    connections.clear()
    authenticated_clients.clear()

    if server_socket:
        server_socket.close()
        server_socket = None

    messages.append("[INFO] Сервер остановлен.")
    update_logs()


# Ожидание подключений
def accept_connections():
    while server_running:
        try:
            client_socket, client_addr = server_socket.accept()
            connections.append((client_socket, client_addr))
            messages.append(f"[INFO] Подключился {client_addr}")
            update_logs()
            threading.Thread(target=handle_client, args=(client_socket, client_addr), daemon=True).start()
        except OSError:
            break


# Обработка клиентов
def handle_client(client_socket, client_addr):
    authenticated_clients[client_socket] = False
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            if not authenticated_clients[client_socket]:  # Ожидаем логин, пароль и ключ доступа
                if "." in data:
                    parts = data.split(".", 2)  # Разделяем строку на 3 части
                    if len(parts) == 3:
                        username, password, access_key = parts
                        password_hash = hashlib.sha256(password.encode()).hexdigest()

                        expected_access_key = str(username_hash(username))

                        if username == USERNAME and password_hash == STORED_PASSWORD_HASH and access_key == expected_access_key:
                            authenticated_clients[client_socket] = True
                            client_socket.sendall("AUTH_SUCCESS\n".encode())
                            messages.append(f"[AUTH] {client_addr} аутентифицирован")
                        else:
                            client_socket.sendall("AUTH_FAIL\n".encode())
                            messages.append(f"[AUTH] Ошибка аутентификации {client_addr} (Неверный логин/пароль/ключ доступа)")
                            client_socket.close()
                            return
                    else:
                        messages.append(f"[WARNING] Неверный формат данных от {client_addr}: {data}")
                        client_socket.sendall("AUTH_FAIL\n".encode())
                        client_socket.close()
                        return
                else:
                    messages.append(f"[WARNING] Неверный формат аутентификации от {client_addr}: {data}")
                    client_socket.sendall("AUTH_FAIL\n".encode())
                    client_socket.close()
                    return
            else:  # Если уже аутентифицирован
                messages.append(f"[{client_addr}] {data}")

            update_logs()  # Теперь сообщения обновляются сразу
    except ConnectionResetError:
        messages.append(f"[INFO] Клиент {client_addr} отключился")
    finally:
        client_socket.close()
        if (client_socket, client_addr) in connections:
            connections.remove((client_socket, client_addr))
        del authenticated_clients[client_socket]
        update_logs()


# Создание UI в Dear PyGui
dpg.create_context()

with dpg.font_registry():
    with dpg.font(font_path, 20) as font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
        dpg.bind_font(font)

with dpg.window(label="Настройки сервера", width=500, height=200):
    dpg.add_text("Порт:")
    dpg.add_input_text(tag="port_input", default_value=str(port), width=150)  # Поле ввода теперь текстовое

    with dpg.group(horizontal=True):
        dpg.add_button(label="Запустить сервер", callback=start_server)
        dpg.add_button(label="Остановить сервер", callback=stop_server)

with dpg.window(label="Лог сервера", width=500, height=300, pos=(0, 220)):
    dpg.add_text(tag="log_messages", wrap=480)  # Теперь текст переносится на новую строку

dpg.create_viewport(title="TCP/IP Server", width=520, height=550)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
