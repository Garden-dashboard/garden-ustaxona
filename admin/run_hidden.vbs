Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "C:\Users\User\GardenUstaxona\admin"
objShell.Run """C:\Users\User\AppData\Local\Programs\Python\Python312\pythonw.exe"" ""C:\Users\User\GardenUstaxona\admin\server.py""", 0, False
