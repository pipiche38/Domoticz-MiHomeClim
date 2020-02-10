"""
<plugin key="MyHomeDirectAPI" name="MyHome direct access API" author="pipiche38" version="1.0.0">
    <params>
        <param field="Address" label="Gateway IP" width="150px" required="true" default="192.168.2.200"/>
        <param field="Port" label="Port" width="30px" required="true" default="20000"/>
        <param field="Mode4" label="list of Mac addresses separated by coma ','" required="true" />
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
                <option label="Logging" value="File"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz

class BasePlugin:

    def __init__(self):
        self.macs = None
        self._connection = None  # connection handle
        self.ack = None
        self.command_state = None
        self.command_trgt = None
        self.command_addr = None
        return

    def onStart(self):
        Domoticz.Log("onStart called")
        Domoticz.Heartbeat(1)
        Domoticz.Log('Mode6: %s' %Parameters["Mode6"])
        list_macs = (Parameters["Mode4"].strip()).split(',')
        self.macs = []
        list_device_mac = []

        # Build list of existing address
        list_device_mac = []
        if len(Devices) > 0:
            for iterDev in Devices:
                list_device_mac.append(Devices[iterDev].DeviceID )

        #Create Widgets if not existing yet
        for addr in list_macs:
            if addr not in list_device_mac:
                Domoticz.Log('Create Widget for %s' %addr)
                unit = len(Devices) + 1
                Options = {"LevelActions": "||||||||||||||||", "LevelNames": "Off|Cmd1|Cmd2|Cmd3|Cmd4|Cmd5|Cmd6|Cmd7|Cmd8|Cmd9|Cmd10|Cmd11|Cmd12|Cmd13|Cmd14|Cmd15",
                           "LevelOffHidden": "false", "SelectorStyle": "1"}
                myDev = Domoticz.Device(DeviceID=addr, Name="Clim " + addr, Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                list_device_mac.append( addr )

        # Open Connection
        self._connection = Domoticz.Connection(Name="MyHome direct API", Transport="TCP/IP", Protocol="None ", Address=Parameters["Address"], Port=Parameters["Port"])
        Domoticz.Log("Connection set: %s" %self._connection)
        return

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
        return

    def onCommand(self, Unit, Command, Level, Color):
        Domoticz.Log( "onCommand - unit: %s, command: %s, level: %s, color: %s" %(Unit, Command, Level, Color))

        if self.command_trgt or self.command_addr or self.ack:
            Domoticz.Error("There is already command in progress - Cmd: %s Addr: %s" %(self.command_trgt, self.command_addr))
            return

        #Retreive device addr
        addr = Devices[Unit].DeviceID

        if Command == 'Off':
            Domoticz.Log("Command Off send to %s" %addr)
            send_command( self._connection, addr, 0)
            # Open channel
            self.command_state = 'Open Channel'
            self.command_trgt = 1
            self.command_addr = addr
            self.ack = False
        elif Command == 'Set Level':
            # Levels are from 10 to 150
            Domoticz.Log("Command Level: %s send to %s" %(Level, addr))
            # Open channel
            self.command_state = 'Open Channel'
            self.command_trgt = (int(Level)+10)//10
            self.command_addr = addr
            self.ack = False
        return

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called for connection: "+Connection.Address+":"+Connection.Port)
        Domoticz.Log("==== Data: %s" %(Data))
        self.ack = True
        return
        
    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection '"+Connection.Name+"'.")
        return

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat - ack: %s state: %s trgt: %s addr: %s" \
                %(self.ack, self.command_state, self.command_trgt, self.command_addr))

        if self.command_state == 'Open Channel':
            self.ack = False
            self.command_state = 'Send Command'
            # Ouverture d'une session Command
            self._connection.Connect()
            data = '*99*0##'
            self._connection.Send(data.encode(), 1)
            Domoticz.Log("==> %s sent" %data.encode())

        if self.command_state == 'Send Command' and self.ack:
            self.ack = False
            self.command_state = 'Close Channel'
            # Command
            data = '*0*'
            data += str(self.command_trgt)
            data += '*'
            data += self.command_addr
            data += '##'
            self._connection.Send(data.encode(), 1)
            Domoticz.Log("==> %s sent" %data.encode())

        if self.command_state == 'Close Channel' and self.ack:
            # Close
            connection.Disconnect()

            self.ack = False
            self.command_state = None
            self.command_trgt = None
            self.command_addr = None

        return



global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def LogMessage(Message):
    if Parameters["Mode6"] != "Normal":
        Domoticz.Log(Message)
    elif Parameters["Mode6"] != "Debug":
        Domoticz.Debug(Message)
    else:
        f = open("http.html","w")
        f.write(Message)
        f.close()   

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")
