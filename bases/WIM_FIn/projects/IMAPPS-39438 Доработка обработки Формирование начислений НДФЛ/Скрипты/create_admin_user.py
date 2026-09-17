#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создает пользователя ИБ admin / 1 в WIM_FIN с админскими ролями,
отключает защиту от опасных действий, пишет элемент справочника Пользователи
и включает его в группу доступа Администраторы.
"""

import sys

import pythoncom
import win32com.client

USER_NAME = "admin"
USER_PASSWORD = "1"
CONN_ANON = "Srvr='localhost';Ref='WIM_FIN';App='PyCOM';Locale=ru_RU;"
CONN_ADMIN = CONN_ANON + "Usr='%s';Pwd='%s';" % (USER_NAME, USER_PASSWORD)

SKIP_ROLE_PREFIXES = ("Запрет",)
SKIP_ROLES = set(["ТолькоПросмотр"])


def safe_print(text):
    """ASCII-safe console output."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def com_err(exc):
    """Extract 1C COM error text."""
    try:
        return str(exc.args[2][2])
    except Exception:
        return str(exc)


def connect(conn_str):
    """Open COM connection."""
    com = win32com.client.Dispatch("V83.COMConnector")
    return com.Connect(conn_str)


def user_name_or_empty(ib_user):
    """Return IB user name or empty if Undefined."""
    if ib_user is None:
        return ""
    try:
        name = ib_user.Имя
        if name is None:
            return ""
        return str(name)
    except Exception:
        return ""


def find_ib_user(conn, name):
    """Find IB user by name; None if missing. Имя в 1С сравнивается без регистра."""
    found = conn.ПользователиИнформационнойБазы.НайтиПоИмени(name)
    found_name = user_name_or_empty(found)
    if found_name and found_name.lower() == name.lower():
        return found
    users = conn.ПользователиИнформационнойБазы.ПолучитьПользователей()
    for item in users:
        item_name = user_name_or_empty(item)
        if item_name.lower() == name.lower():
            return item
    return None


def role_name(role):
    """Metadata role name."""
    try:
        return str(role.Имя)
    except Exception:
        return ""


def should_skip_role(name):
    """Skip restriction and view-only roles."""
    if not name:
        return True
    if name in SKIP_ROLES:
        return True
    for prefix in SKIP_ROLE_PREFIXES:
        if name.startswith(prefix):
            return True
    return False


def assign_admin_roles(conn, ib_user):
    """Assign all non-restriction configuration roles."""
    try:
        ib_user.Роли.Очистить()
    except Exception:
        try:
            while ib_user.Роли.Количество() > 0:
                ib_user.Роли.Удалить(0)
        except Exception:
            pass

    added = []
    skipped = []
    roles_md = conn.Метаданные.Роли
    count = roles_md.Количество()
    for index in range(count):
        role = roles_md.Получить(index)
        name = role_name(role)
        if should_skip_role(name):
            skipped.append(name)
            continue
        ib_user.Роли.Добавить(role)
        added.append(name)
    return added, skipped


def ensure_catalog_user(conn, ib_user):
    """Create or update catalog Пользователи linked to IB user."""
    uuid = ib_user.УникальныйИдентификатор
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.Пользователи "
        "ГДЕ ИдентификаторПользователяИБ = &Ид ИЛИ Наименование = &Имя"
    )
    query.УстановитьПараметр("Ид", uuid)
    query.УстановитьПараметр("Имя", USER_NAME)
    result = query.Выполнить()
    if result.Пустой():
        manager = conn.NewObject("СправочникМенеджер.Пользователи")
        obj = manager.СоздатьЭлемент()
        created = True
    else:
        obj = result.Выгрузить()[0].Ссылка.ПолучитьОбъект()
        created = False
    obj.Наименование = USER_NAME
    obj.ИдентификаторПользователяИБ = uuid
    try:
        obj.Недействителен = False
    except Exception:
        pass
    obj.ОбменДанными.Загрузка = True
    obj.Записать()
    return obj.Ссылка, created


def ensure_admins_group(conn, user_ref):
    """Add catalog user into predefined group Администраторы."""
    query = conn.NewObject("Запрос")
    query.Текст = (
        "ВЫБРАТЬ ПЕРВЫЕ 1 Ссылка ИЗ Справочник.ГруппыДоступа "
        "ГДЕ Ссылка = ЗНАЧЕНИЕ(Справочник.ГруппыДоступа.Администраторы)"
    )
    result = query.Выполнить()
    if result.Пустой():
        return "group Administratory not found"
    group_ref = result.Выгрузить()[0].Ссылка
    obj = group_ref.ПолучитьОбъект()
    already = False
    for row in obj.Пользователи:
        try:
            if str(row.Пользователь) == str(user_ref):
                already = True
                break
        except Exception:
            continue
    if not already:
        row = obj.Пользователи.Добавить()
        row.Пользователь = user_ref
        obj.ОбменДанными.Загрузка = True
        obj.Записать()
        return "added to Administratory"
    return "already in Administratory"


def list_users(conn):
    """Return IB user names."""
    users = conn.ПользователиИнформационнойБазы.ПолучитьПользователей()
    names = []
    for item in users:
        names.append(user_name_or_empty(item) or "<empty>")
    return names


def list_user_roles(ib_user):
    """Return role names of IB user."""
    roles_now = []
    for role in ib_user.Роли:
        name = role_name(role)
        if name:
            roles_now.append(name)
        else:
            roles_now.append(str(role))
    return roles_now


def main():
    pythoncom.CoInitialize()
    conn = None
    try:
        try:
            conn = connect(CONN_ADMIN)
            safe_print("CONNECT=admin/1 OK")
        except Exception as exc:
            safe_print("CONNECT admin/1 FAIL: %s" % com_err(exc))
            conn = connect(CONN_ANON)
            safe_print("CONNECT=anonymous OK")

        try:
            conn.УстановитьПроверкуСложностиПаролейПользователей(False)
            conn.УстановитьМинимальнуюДлинуПаролейПользователей(0)
            safe_print("PASSWORD_POLICY=off")
        except Exception as exc:
            safe_print("PASSWORD_POLICY FAIL: %s" % com_err(exc))

        before = list_users(conn)
        safe_print("USERS_BEFORE=%s" % (",".join(before) if before else "<none>"))

        ib_user = find_ib_user(conn, USER_NAME)
        created = False
        if ib_user is None:
            ib_user = conn.ПользователиИнформационнойБазы.СоздатьПользователя()
            created = True
            safe_print("IB_USER=create")
        else:
            safe_print("IB_USER=update")

        ib_user.Имя = USER_NAME
        ib_user.ПолноеИмя = USER_NAME
        ib_user.Пароль = USER_PASSWORD
        ib_user.АутентификацияСтандартная = True
        ib_user.ПоказыватьВСпискеВыбора = True
        try:
            ib_user.ЗапрещеноИзменятьПароль = False
        except Exception:
            pass
        try:
            ib_user.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях = False
            safe_print("DANGEROUS_ACTIONS=off")
        except Exception as exc:
            safe_print("DANGEROUS_ACTIONS FAIL: %s" % com_err(exc))

        added, skipped = assign_admin_roles(conn, ib_user)
        safe_print("ROLES_COUNT=%s" % len(added))
        safe_print("ROLES=%s" % ",".join(added))
        if skipped:
            safe_print("ROLES_SKIPPED=%s" % ",".join(skipped))

        ib_user.Записать()
        safe_print("IB_USER_WRITTEN=%s" % ("created" if created else "updated"))

        try:
            cat_ref, cat_created = ensure_catalog_user(conn, ib_user)
            safe_print("CATALOG_USER=%s" % ("created" if cat_created else "updated"))
            group_msg = ensure_admins_group(conn, cat_ref)
            safe_print("ACCESS_GROUP=%s" % group_msg)
        except Exception as exc:
            safe_print("CATALOG_OR_GROUP FAIL: %s" % com_err(exc))

        del conn
        conn = None
        conn2 = connect(CONN_ADMIN)
        cur = conn2.ПользователиИнформационнойБазы.ТекущийПользователь()
        safe_print("RELOGIN=OK name=%s" % user_name_or_empty(cur))
        roles_now = list_user_roles(cur)
        safe_print("RELOGIN_ROLES_COUNT=%s" % len(roles_now))
        safe_print("RELOGIN_ROLES=%s" % ",".join(roles_now))
        try:
            warn = cur.ЗащитаОтОпасныхДействий.ПредупреждатьОбОпасныхДействиях
            safe_print("RELOGIN_DANGEROUS_WARN=%s" % warn)
        except Exception as exc:
            safe_print("RELOGIN_DANGEROUS FAIL: %s" % com_err(exc))
        del conn2
        safe_print("DONE=OK")
        return 0
    except Exception as exc:
        safe_print("FAIL=%s" % com_err(exc))
        return 1
    finally:
        if conn is not None:
            del conn
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
