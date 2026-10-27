# -*- coding: utf-8 -*-
"""IMAPPS-40325: завершает простаивающие сеансы COMConnection базы WIM_DU, начатые сегодня (остаются от
COM-скриптов стенда, завершенных os._exit). Сеансы других приложений и с активным вызовом не трогает."""
import datetime
import os
import sys
import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
agent = win32com.client.Dispatch("V83.COMConnector").ConnectAgent("tcp://localhost:1540")
cluster = agent.GetClusters()[0]
agent.Authenticate(cluster, "", "")
today = datetime.date.today()
done = 0
for s in agent.GetSessions(cluster):
    if s.InfoBase.Name.upper() != "WIM_DU" or s.AppID != "COMConnection" or s.DurationCurrent != 0:
        continue
    started = s.StartedAt
    if datetime.date(started.year, started.month, started.day) != today:
        print("пропущен (не сегодня)", s.SessionID, started)
        continue
    try:
        agent.TerminateSession(cluster, s)
        done += 1
    except Exception as e:
        print("пропущен", s.SessionID, e)
print("завершено сеансов:", done)
sys.stdout.flush()
os._exit(0)
