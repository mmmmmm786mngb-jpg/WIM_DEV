# Завершает простаивающие сеансы COMConnection базы WIM_DU (остаются от COM-скриптов стенда, завершенных os._exit).
import win32com.client, os, sys
a = win32com.client.Dispatch("V83.COMConnector").ConnectAgent("tcp://localhost:1540")
cl = a.GetClusters()[0]; a.Authenticate(cl, "", "")
n = 0
for s in a.GetSessions(cl):
    if s.InfoBase.Name.upper() == "WIM_DU" and s.AppID == "COMConnection" and s.DurationCurrent == 0:
        try:
            a.TerminateSession(cl, s); n += 1
        except Exception as e:
            print("skip", s.SessionID, e)
print("terminated", n)
sys.stdout.flush(); os._exit(0)
