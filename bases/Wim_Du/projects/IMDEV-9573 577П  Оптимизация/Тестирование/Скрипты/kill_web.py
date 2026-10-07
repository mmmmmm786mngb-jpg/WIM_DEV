# Завершает сеансы WebClient базы WIM_DU (брошенные после падения вкладки браузера стенда).
import win32com.client, os, sys
a = win32com.client.Dispatch("V83.COMConnector").ConnectAgent("tcp://localhost:1540")
cl = a.GetClusters()[0]; a.Authenticate(cl, "", "")
for s in a.GetSessions(cl):
    if s.InfoBase.Name.upper() == "WIM_DU" and s.AppID == "WebClient":
        a.TerminateSession(cl, s); print("terminated", s.SessionID)
sys.stdout.flush(); os._exit(0)
