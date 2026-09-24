#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создает пользователя admin в серверной базе WIN_FO_server
и назначает ему роли пользователя admin файловой базы.
"""

import pythoncom
import win32com.client

FILE_CONN = "File='C:\\1c\\Cursor_1c\\WORK\\WIM_Fo';Usr='admin';Pwd='1';App='PyCOM';Locale=ru_RU;"
SERVER_CONN = "Srvr='localhost';Ref='WIN_FO_server';App='PyCOM';Locale=ru_RU;"


def role_names(conn, user):
    names = []
    for role in user.Роли:
        names.append(conn.String(role.Имя))
    return names


def metadata_role(conn, name):
    for role in conn.Метаданные.Роли:
        if conn.String(role.Имя) == name:
            return role
    return None


def main():
    pythoncom.CoInitialize()
    connector = win32com.client.Dispatch("V83.COMConnector")
    file_conn = connector.Connect(FILE_CONN)
    file_user = file_conn.ПользователиИнформационнойБазы.НайтиПоИмени("admin")
    names = role_names(file_conn, file_user)
    print("file roles", ", ".join(names))

    server = connector.Connect(SERVER_CONN)
    users = server.ПользователиИнформационнойБазы
    user = users.НайтиПоИмени("admin")
    if user is None:
        user = users.СоздатьПользователя()
        print("created new user")
    else:
        print("user already exists")
    user.Имя = "admin"
    user.ПолноеИмя = "admin"
    user.Пароль = "1"
    user.АутентификацияСтандартная = True
    user.АутентификацияОС = False
    user.ПоказыватьВСпискеВыбора = True
    user.Роли.Очистить()
    missing = []
    for name in names:
        role = metadata_role(server, name)
        if role is None:
            missing.append(name)
            continue
        user.Роли.Добавить(role)
    user.Записать()

    saved = users.НайтиПоИмени("admin")
    saved_roles = role_names(server, saved)
    print("server roles", ", ".join(saved_roles))
    print("password set", saved.ПарольУстановлен)
    print("standard", saved.АутентификацияСтандартная)
    if missing:
        print("missing", ", ".join(missing))
    print("USER DONE")


if __name__ == "__main__":
    main()
