from enigma import eServiceCenter, eServiceReference, iServiceInformation, eTimer, eConsoleAppContainer
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap
from Components.ProgressBar import ProgressBar
from Components.Button import Button
import os
import xml.etree.ElementTree as ET
import urllib.parse
import subprocess
import time
import re


class AstraAnalyzeScreen(Screen):
    skin = """
    <screen name="AstraAnalyzeScreen" position="center,center" size="1800,900" title="..:: Astra-SM Analyze Results ::..">
        <!-- Pozadina -->
        <eLabel position="0,0" size="1400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <!-- Pozadina desno -->
        <eLabel position="1400,500" size="400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <widget name="background2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/background2.png" position="1400,0" size="400,500" />
        <!-- Rezultati analize -->
        <widget name="analyze_results" position="20,20" size="1360,880" 
                font="Console;20" transparent="1" foregroundColor="white" />
        <!-- Naslov -->
        <widget source="Title" render="Label" position="1400,550" size="400,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" backgroundColor="#0D1B36" />
         <!-- Dugmad -->
        <widget name="key_red" position="1440,650" size="320,40" 
                backgroundColor="red" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_green" position="1440,720" size="320,40" 
                backgroundColor="green" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_yellow" position="1440,790" size="320,40" 
                backgroundColor="yellow" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" /> 
    </screen>
    """

    def __init__(self, session, analyze_output, container, parent, pid=None):
        Screen.__init__(self, session)
        self.analyze_output = analyze_output
        self.container = container
        self.parent = parent
        self.pid = pid
        self["analyze_results"] = ScrollLabel("")
        self["key_red"] = Button("Back")
        self["key_green"] = Button("Save to File")
        self["key_yellow"] = Button("Stop Analysis")
        self["background2"] = Pixmap()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
                                    {
                                        "ok": self.close,
                                        "cancel": self.close,
                                        "red": self.close,
                                        "green": self.saveToFile,
                                        "yellow": self.stopAnalysis,
                                        "up": self["analyze_results"].pageUp,
                                        "down": self["analyze_results"].pageDown,
                                    }, -2)

        self.onLayoutFinish.append(self.showResults)

    def showResults(self):
        print("[AstraAnalyzeScreen] Showing results")
        self["analyze_results"].setText("\n".join(self.analyze_output))

    def updateResults(self):
        print("[AstraAnalyzeScreen] Updating results")
        self["analyze_results"].setText("\n".join(self.analyze_output))

    def saveToFile(self):
        print("[AstraAnalyzeScreen] Saving results to file")
        try:
            dir_path = "/tmp/CiefpSatelliteAnalyzer"
            os.makedirs(dir_path, exist_ok=True)
            pid_str = f"pid{self.pid}" if self.pid else "no_pid"
            date_str = time.strftime('%Y%m%d')
            provider = "Unknown"
            for line in self.analyze_output:
                if 'Provider:' in line:
                    provider_match = re.search(r'Provider:\s*(.+)', line)
                    if provider_match:
                        provider = provider_match.group(1).strip().replace(" ", "_")
                        break
            satellite = "Unknown"
            service = self.session.nav.getCurrentService()
            if service:
                frontendInfo = service.frontendInfo()
                if frontendInfo:
                    frontendData = frontendInfo.getAll(True)
                    if frontendData:
                        try:
                            orbital_pos = frontendData.get("orbital_position", 0)
                            satellite = self.parent.formatOrbitalPos(orbital_pos)
                        except Exception as e:
                            print(f"[AstraAnalyzeScreen] Error getting satellite info: {str(e)}")
                            satellite = "Unknown"
            filename = f"{dir_path}/astra_analyze_{provider}_{satellite}_{date_str}_{pid_str}.log"
            with open(filename, 'w') as f:
                f.write("\n".join(self.analyze_output))
            self.session.open(MessageBox, f"Results saved to:\n{filename}", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"[AstraAnalyzeScreen] Error saving file: {str(e)}")
            self.session.open(MessageBox, f"Error saving file:\n{str(e)}", MessageBox.TYPE_ERROR)

    def stopAnalysis(self):
        print("[AstraAnalyzeScreen] Initiating stopAnalysis")
        try:
            if self.container:
                print("[AstraAnalyzeScreen] Killing container process")
                self.container.kill()
                os.system("systemctl stop astra-sm")
                print("[AstraAnalyzeScreen] Executed systemctl stop astra-sm")
                time.sleep(0.5)
                if os.system("pidof astra >/dev/null") == 0:
                    print("[AstraAnalyzeScreen] Warning: astra process still running after stop")
                else:
                    print("[AstraAnalyzeScreen] astra process successfully terminated")
                self.container = None
            else:
                print("[AstraAnalyzeScreen] No container to kill")
            if self.parent:
                print("[AstraAnalyzeScreen] Calling parent.stopAnalysisCleanup")
                self.parent.stopAnalysisCleanup()
            else:
                print("[AstraAnalyzeScreen] No parent instance available")
            print("[AstraAnalyzeScreen] Closing screen")
            self.close()
        except Exception as e:
            print(f"[AstraAnalyzeScreen] Error in stopAnalysis: {str(e)}")
            self.session.open(MessageBox, f"Error stopping analysis: {str(e)}", MessageBox.TYPE_ERROR)

class AbertisAnalyzeScreen(Screen):
    skin = """
    <screen name="AbertisAnalyzeScreen" position="center,center" size="1800,900" title="..:: Abertis Analyze Results ::..">
        <!-- Pozadina -->
        <eLabel position="0,0" size="1400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <!-- Pozadina desno -->
        <eLabel position="1400,500" size="400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <widget name="background2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/background3.png" position="1400,0" size="400,500" />
        <!-- Rezultati analize -->
        <widget name="analyze_results" position="20,20" size="1360,880" 
                font="Console;20" transparent="1" foregroundColor="white" />
        <!-- Naslov -->
        <widget source="Title" render="Label" position="1400,550" size="400,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" backgroundColor="#0D1B36" />
         <!-- Dugmad -->
        <widget name="key_red" position="1440,650" size="320,40" 
                backgroundColor="red" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_green" position="1440,720" size="320,40" 
                backgroundColor="green" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_yellow" position="1440,790" size="320,40" 
                backgroundColor="yellow" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" /> 
    </screen>
    """

    def __init__(self, session, analyze_output, container, parent, pid=None):
        Screen.__init__(self, session)
        self.analyze_output = analyze_output
        self.container = container
        self.parent = parent
        self.pid = pid
        self["analyze_results"] = ScrollLabel("")
        self["key_red"] = Button("Back")
        self["key_green"] = Button("Save to File")
        self["key_yellow"] = Button("Stop Analysis")
        self["background2"] = Pixmap()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
                                    {
                                        "ok": self.close,
                                        "cancel": self.close,
                                        "red": self.close,
                                        "green": self.saveToFile,
                                        "yellow": self.stopAnalysis,
                                        "up": self["analyze_results"].pageUp,
                                        "down": self["analyze_results"].pageDown,
                                    }, -2)

        self.onLayoutFinish.append(self.showResults)

    def showResults(self):
        print("[AbertisAnalyzeScreen] Showing results")
        self["analyze_results"].setText("\n".join(self.analyze_output))

    def updateResults(self):
        print("[AbertisAnalyzeScreen] Updating results")
        self["analyze_results"].setText("\n".join(self.analyze_output))

    def saveToFile(self):
        print("[AbertisAnalyzeScreen] Saving results to file")
        try:
            dir_path = "/tmp/CiefpSatelliteAnalyzer"
            os.makedirs(dir_path, exist_ok=True)
            pid_str = f"pid{self.pid}" if self.pid else "no_pid"
            date_str = time.strftime('%Y%m%d')
            provider = "Unknown"
            for line in self.analyze_output:
                if 'Provider:' in line:
                    provider_match = re.search(r'Provider:\s*(.+)', line)
                    if provider_match:
                        provider = provider_match.group(1).strip().replace(" ", "_")
                        break
            satellite = "Unknown"
            service = self.session.nav.getCurrentService()
            if service:
                frontendInfo = service.frontendInfo()
                if frontendInfo:
                    frontendData = frontendInfo.getAll(True)
                    if frontendData:
                        try:
                            orbital_pos = frontendData.get("orbital_position", 0)
                            satellite = self.parent.formatOrbitalPos(orbital_pos)
                        except Exception as e:
                            print(f"[AbertisAnalyzeScreen] Error getting satellite info: {str(e)}")
                            satellite = "Unknown"
            filename = f"{dir_path}/abertis_analyze_{provider}_{satellite}_{date_str}_{pid_str}.log"
            with open(filename, 'w') as f:
                f.write("\n".join(self.analyze_output))
            self.session.open(MessageBox, f"Results saved to:\n{filename}", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"[AbertisAnalyzeScreen] Error saving file: {str(e)}")
            self.session.open(MessageBox, f"Error saving file:\n{str(e)}", MessageBox.TYPE_ERROR)

    def stopAnalysis(self):
        print("[AbertisAnalyzeScreen] Initiating stopAnalysis")
        try:
            if self.container:
                print("[AbertisAnalyzeScreen] Killing container process")
                self.container.kill()
                os.system("systemctl stop astra-sm")
                print("[AbertisAnalyzeScreen] Executed systemctl stop astra-sm")
                time.sleep(0.5)
                if os.system("pidof astra >/dev/null") == 0:
                    print("[AbertisAnalyzeScreen] Warning: astra process still running after stop")
                else:
                    print("[AbertisAnalyzeScreen] astra process successfully terminated")
                self.container = None
            else:
                print("[AbertisAnalyzeScreen] No container to kill")
            if self.parent:
                print("[AbertisAnalyzeScreen] Calling parent.stopAnalysisCleanup")
                self.parent.stopAnalysisCleanup()
            else:
                print("[AbertisAnalyzeScreen] No parent instance available")
            print("[AbertisAnalyzeScreen] Closing screen")
            self.close()
        except Exception as e:
            print(f"[AbertisAnalyzeScreen] Error in stopAnalysis: {str(e)}")
            self.session.open(MessageBox, f"Error stopping analysis: {str(e)}", MessageBox.TYPE_ERROR)

class SatelliteAnalyzer(Screen):
    skin = """
    <screen name="SatelliteAnalyzer" position="center,center" size="1800,900" title="..:: Ciefp Satellite Analyzer ::..">
        <!-- Pozadina desno -->
        <eLabel position="1400,500" size="400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <!-- Logo (400x500) -->
        <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/background.png" position="1400,0" size="400,500" />
        <!-- Naslov -->
        <widget source="Title" render="Label" position="1400,520" size="400,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" backgroundColor="#0D1B36" />
        <!-- Vrijeme -->
        <widget name="time" position="1400,570" size="400,40" 
                font="Regular;24" halign="center" valign="center" foregroundColor="#BBBBBB" backgroundColor="#0D1B36" />
         <!-- Dugmad -->
        <widget name="key_red" position="1440,620" size="320,40" 
                backgroundColor="red" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_green" position="1440,670" size="320,40" 
                backgroundColor="green" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <widget name="key_yellow" position="1440,720" size="320,40" 
                backgroundColor="yellow" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />  
        <widget name="key_blue" position="1440,770" size="320,40" 
                backgroundColor="blue" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
        <!-- LEVO: Osnovni info -->
        <widget name="info_left" position="20,20" size="680,800" 
                font="Console;24" transparent="1" />
        <!-- SREDINA: Kodiranje, Signal, SI/TS/ONID -->
        <widget name="info_center" position="720,20" size="680,800" 
                font="Console;24" transparent="1" />
        <!-- DONJI DEO: SNR i AGC TRAKE -->
        <widget name="snr_label" position="20,820" size="100,24" font="Regular;20" halign="left" valign="center" foregroundColor="white" />
        <widget name="snr_bar" position="120,820" size="1180,24" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/icon_snr.png" borderWidth="2" borderColor="green" />
        <widget name="agc_label" position="20,864" size="100,24" font="Regular;20" halign="left" valign="center" foregroundColor="white" />
        <widget name="agc_bar" position="120,864" size="1180,24" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/icon_agc.png" borderWidth="2" borderColor="green" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["info_left"] = ScrollLabel("")
        self["info_center"] = ScrollLabel("")
        self["astra_results"] = Label("")
        self["time"] = Label("")
        self["key_red"] = Label("Back")
        self["key_green"] = Label("Create Bouquet")
        self["key_yellow"] = Label("Astra Analyze")
        self["key_blue"] = Label("Abertis Scan")
        self["background"] = Pixmap()
        self["snr_label"] = Label("SNR:")
        self["snr_bar"] = ProgressBar()
        self["agc_label"] = Label("AGC:")
        self["agc_bar"] = ProgressBar()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
                                    {
                                        "ok": self.close,
                                        "cancel": self.close,
                                        "red": self.close,
                                        "green": self.createBouquet,
                                        "yellow": self.startAstraAnalyze,
                                        "blue": self.startAbertisAnalyze,
                                        "up": self["info_left"].pageUp,
                                        "down": self["info_left"].pageDown,
                                    }, -2)

        self.time_update_timer = eTimer()
        self.time_update_timer.callback.append(self.updateTime)
        self.time_update_timer.start(1000)
        self.onClose.append(self.time_update_timer.stop)

        self.signal_update_timer = eTimer()
        self.signal_update_timer.callback.append(self.updateAllInfo)
        self.signal_update_timer.start(5000)
        self.onClose.append(self.signal_update_timer.stop)

        self.onLayoutFinish.append(self.updateInfo)

        self.astra_options = [
            ("4095 - c:150fff", "t2mi://#t2mi_pid=4095&t2mi_input=http://127.0.0.1:8001/-----:", "4095"),
            ("4096 - c:151000", "t2mi://#t2mi_pid=4096&t2mi_input=http://127.0.0.1:8001/-----:", "4096"),
            ("4096 - c:151000 plp2", "t2mi://#t2mi_pid=4096&t2mi_plp=2&t2mi_input=http://127.0.0.1:8001/-----:", "4096_plp2"),
            ("4097 - c:151001", "t2mi://#t2mi_pid=4097&t2mi_input=http://127.0.0.1:8001/-----:", "4097"),
            ("4706 - c:151262", "t2mi://#t2mi_pid=4706&t2mi_input=http://127.0.0.1:8001/-----:", "4706"),
            ("4716 - c:15126C", "t2mi://#t2mi_pid=4716&t2mi_input=http://127.0.0.1:8001/-----:", "4716"),
            ("4219 - c:15107B", "t2mi://#t2mi_pid=4219&t2mi_input=http://127.0.0.1:8001/-----:", "4219"),
            ("4646 - c:151226", "t2mi://#t2mi_pid=4646&t2mi_input=http://127.0.0.1:8001/-----:", "4646"),
            ("4102 - c:151006", "t2mi://#t2mi_pid=4102&t2mi_input=http://127.0.0.1:8001/-----:", "4102"),
            ("4105 - c:151009", "t2mi://#t2mi_pid=4105&t2mi_input=http://127.0.0.1:8001/-----:", "4105"),
            ("Default (no T2MI)", "http://127.0.0.1:8001/-----:", "no_t2mi")
        ]

        self.abertis_pids = [
            "301", "303", "420", "421", "423", "701", "702", "703", "801",
            "2025", "2026", "2027", "2028", "2050", "2060", "2270", "2271",
            "2272", "2273", "2274", "2302", "2303", "2305", "2306", "2308",
            "2520", "2521", "2522", "2523", "2524", "8000", "8001", "8002",
            "8003", "8004", "8005", "8006"
        ]
        self.abertis_options = [(pid, f"http://127.0.0.1:9999/abertis/pid{pid}", pid) for pid in self.abertis_pids]
        self.astra_output = []
        self.analyzing = False
        self.astra_analyze_screen = None
        self.abertis_analyze_screen = None
        self.container = None

    def close(self):
        print("[SatelliteAnalyzer] Initiating close")
        if self.analyzing:
            print("[SatelliteAnalyzer] Analysis in progress, showing warning")
            self.session.open(MessageBox, _("The analysis is in progress, please wait or press the yellow button on the analysis screen to stop!"), MessageBox.TYPE_INFO, timeout=5)
            return
        if self.astra_analyze_screen:
            print("[SatelliteAnalyzer] Closing astra_analyze_screen")
            self.astra_analyze_screen.close()
            self.astra_analyze_screen = None
        if self.abertis_analyze_screen:
            print("[SatelliteAnalyzer] Closing abertis_analyze_screen")
            self.abertis_analyze_screen.close()
            self.abertis_analyze_screen = None
        if self.container:
            print("[SatelliteAnalyzer] Killing container in close")
            self.container.kill()
            os.system("systemctl stop astra-sm")
            print("[SatelliteAnalyzer] Executed systemctl stop astra-sm")
            time.sleep(0.5)
            if os.system("pidof astra >/dev/null") == 0:
                print("[SatelliteAnalyzer] Warning: astra process still running after stop")
            else:
                print("[SatelliteAnalyzer] astra process successfully terminated")
            self.container = None
        self.resetTunerAndStream()
        print("[SatelliteAnalyzer] Closing SatelliteAnalyzer screen")
        Screen.close(self)

    def stopAnalysisCleanup(self):
        print("[SatelliteAnalyzer] Cleaning up after analysis stopped")
        try:
            self.analyzing = False
            if self.container:
                print("[SatelliteAnalyzer] Killing container in stopAnalysisCleanup")
                self.container.kill()
                os.system("systemctl stop astra-sm")
                print("[SatelliteAnalyzer] Executed systemctl stop astra-sm")
                time.sleep(0.5)
                if os.system("pidof astra >/dev/null") == 0:
                    print("[SatelliteAnalyzer] Warning: astra process still running after stop")
                else:
                    print("[SatelliteAnalyzer] astra process successfully terminated")
                self.container = None
            if self.astra_analyze_screen:
                print("[SatelliteAnalyzer] Closing astra_analyze_screen in stopAnalysisCleanup")
                self.astra_analyze_screen.close()
                self.astra_analyze_screen = None
            if self.abertis_analyze_screen:
                print("[SatelliteAnalyzer] Closing abertis_analyze_screen in stopAnalysisCleanup")
                self.abertis_analyze_screen.close()
                self.abertis_analyze_screen = None
            self.resetTunerAndStream()
        except Exception as e:
            print(f"[SatelliteAnalyzer] Error in stopAnalysisCleanup: {str(e)}")

    def resetTunerAndStream(self):
        print("[SatelliteAnalyzer] Resetting tuner and stream resources")
        try:
            resource_manager = eDVBResourceManager.getInstance()
            if resource_manager:
                print("[SatelliteAnalyzer] Releasing cached channel")
                resource_manager.releaseCachedChannel()
            else:
                print("[SatelliteAnalyzer] Warning: eDVBResourceManager not available")
            self.session.nav.stopService()
            print("[SatelliteAnalyzer] Stopped current service")
            if os.path.exists("/usr/bin/streamrelay"):
                print("[SatelliteAnalyzer] Restarting streamrelay")
                os.system("killall -9 streamrelay")
                time.sleep(0.5)
                os.system("/usr/bin/streamrelay &")
                print("[SatelliteAnalyzer] Streamrelay restarted")
            else:
                print("[SatelliteAnalyzer] Streamrelay binary not found")
            print("[SatelliteAnalyzer] Restarting astra-sm service")
            os.system("systemctl restart astra-sm")
            print("[SatelliteAnalyzer] Executed systemctl restart astra-sm")
            if os.system("netstat -tuln | grep :8001 >/dev/null") != 0:
                print("[SatelliteAnalyzer] Warning: e2stream server (port 8001) not running")
            else:
                print("[SatelliteAnalyzer] e2stream server (port 8001) is running")
        except Exception as e:
            print(f"[SatelliteAnalyzer] Error in resetTunerAndStream: {str(e)}")

    def updateTime(self):
        try:
            import time
            t = time.strftime("%H:%M:%S")
            self["time"].setText(t)
        except:
            pass

    def updateInfo(self):
        self.updateAllInfo()

    def updateAllInfo(self):
        left_text = self.getBasicInfo()
        center_text = self.getAdvancedInfo()
        self["info_left"].setText(left_text)
        self["info_center"].setText(center_text)
        snr_db, snr_percent, ber, agc, is_crypted, sid, tsid, onid = self.getSignalFromFrontend()
        self.updateSignalBars(snr_percent, agc)

    def updateSignalBars(self, snr_percent, agc):
        print(f"[SatelliteAnalyzer] Update signal bars: SNR={snr_percent}%, AGC={agc}%")
        try:
            self["snr_bar"].setValue(int(snr_percent))
            self["agc_bar"].setValue(int(agc))
        except Exception as e:
            print(f"[SatelliteAnalyzer] Error updating bars: {e}")

    def getSignalFromFrontend(self):
        service = self.session.nav.getCurrentService()
        if service:
            frontendInfo = service.frontendInfo()
            if frontendInfo:
                try:
                    frontendData = frontendInfo.getAll(True)
                    print(f"[SatelliteAnalyzer] Raw frontend data: {frontendData}")
                    quality = frontendData.get("tuner_signal_quality", 0)
                    snr_percent = min(100, quality // 655)
                    snr_db = frontendData.get("tuner_signal_quality_db", 0) / 100.0
                    ber = frontendData.get("tuner_bit_error_rate", 0)
                    agc = min(100, frontendData.get("tuner_signal_power", 0) // 655)
                    service_info = service.info()
                    is_crypted = service_info.getInfo(iServiceInformation.sIsCrypted)
                    sid = service_info.getInfo(iServiceInformation.sSID)
                    tsid = service_info.getInfo(iServiceInformation.sTSID)
                    onid = service_info.getInfo(iServiceInformation.sONID)
                    print(
                        f"[SatelliteAnalyzer] Frontend data: SNR_DB={snr_db}, SNR_PERCENT={snr_percent}, BER={ber}, AGC={agc}, Crypted={is_crypted}, SID={sid}, TSID={tsid}, ONID={onid}")
                    return snr_db, snr_percent, ber, agc, is_crypted, sid, tsid, onid
                except Exception as e:
                    print(f"[SatelliteAnalyzer] Error retrieving signal from frontend: {e}")
        return 0.0, 0, 0, 0, 0, 0, 0, 0

    def getServiceReference(self):
        service = self.session.nav.getCurrentService()
        if service:
            service_ref = self.session.nav.getCurrentlyPlayingServiceReference()
            if service_ref:
                return service_ref.toString()
        return "N/A"

    def startAstraAnalyze(self):
        print("[SatelliteAnalyzer] Starting astra analyze")
        service_ref = self.getServiceReference()
        print(f"[SatelliteAnalyzer] Service reference: {service_ref}")
        if service_ref == "N/A":
            print("[SatelliteAnalyzer] No active service for analysis")
            self.session.open(MessageBox, _("No active service for analysis!"), MessageBox.TYPE_ERROR)
            return
        if not os.path.exists("/usr/bin/astra"):
            print("[SatelliteAnalyzer] Error: astra-sm not found at /usr/bin/astra")
            self.session.open(MessageBox, _("Error: astra-sm not found. Please install astra-sm."), MessageBox.TYPE_ERROR)
            return
        print("[SatelliteAnalyzer] Opening ChoiceBox for analysis options")
        self.session.openWithCallback(self.onAnalyzeSelected, ChoiceBox, title=_("Select Analyze Option"), list=[(opt[0], opt) for opt in self.astra_options])

    def startAbertisAnalyze(self):
        print("[SatelliteAnalyzer] Starting abertis analyze")
        service_ref = self.getServiceReference()
        print(f"[SatelliteAnalyzer] Service reference: {service_ref}")
        if service_ref == "N/A":
            print("[SatelliteAnalyzer] No active service for analysis")
            self.session.open(MessageBox, _("No active service for analysis!"), MessageBox.TYPE_ERROR)
            return
        if not os.path.exists("/usr/bin/astra"):
            print("[SatelliteAnalyzer] Error: astra-sm not found at /usr/bin/astra")
            self.session.open(MessageBox, _("Error: astra-sm not found. Please install astra-sm."), MessageBox.TYPE_ERROR)
            return
        print("[SatelliteAnalyzer] Opening ChoiceBox for Abertis PID options")
        self.session.openWithCallback(self.onAbertisAnalyzeSelected, ChoiceBox, title=_("Select Abertis PID"), list=[(opt[0], opt) for opt in self.abertis_options])

    def onAnalyzeSelected(self, choice):
        print("[SatelliteAnalyzer] onAnalyzeSelected called with choice:", choice)
        if choice:
            try:
                option = choice[1]
                pid = option[2]
                self.analyzing = True
                self.astra_output = []
                self.container = eConsoleAppContainer()
                print("[SatelliteAnalyzer] Created eConsoleAppContainer")
                self.astra_analyze_screen = self.session.open(AstraAnalyzeScreen, self.astra_output, self.container, self, pid=pid)
                print("[SatelliteAnalyzer] Opened AstraAnalyzeScreen")
                self.session.open(MessageBox, _("Analysis in progress, wait a few seconds or press the yellow button to stop."), MessageBox.TYPE_INFO, timeout=5)
                cmd_template = option[1]
                service_ref = self.getServiceReference()
                if service_ref == "N/A":
                    print("[SatelliteAnalyzer] Error: Service reference became invalid")
                    self.session.open(MessageBox, _("Error: Service reference lost during analysis."), MessageBox.TYPE_ERROR)
                    self.stopAnalysisCleanup()
                    return
                cmd = cmd_template.replace("-----:", f"{service_ref}:")
                cmd = f'astra --analyze "{cmd}"'
                print(f"[SatelliteAnalyzer] Executing command: {cmd}")
                self.container.appClosed.append(self.onAnalyzeFinished)
                self.container.dataAvail.append(self.onDataAvail)
                self.container.execute(cmd)
                print("[SatelliteAnalyzer] Command executed")
            except Exception as e:
                print(f"[SatelliteAnalyzer] Error in onAnalyzeSelected: {str(e)}")
                self.session.open(MessageBox, f"Error starting analysis: {str(e)}", MessageBox.TYPE_ERROR)
                self.stopAnalysisCleanup()
        else:
            print("[SatelliteAnalyzer] No choice selected, cancelling analysis")

    def onAbertisAnalyzeSelected(self, choice):
        print("[SatelliteAnalyzer] onAbertisAnalyzeSelected called with choice:", choice)
        if choice:
            try:
                option = choice[1]
                pid = option[2]
                self.analyzing = True
                self.astra_output = []
                self.container = eConsoleAppContainer()
                print("[SatelliteAnalyzer] Created eConsoleAppContainer for Abertis")
                self.abertis_analyze_screen = self.session.open(AbertisAnalyzeScreen, self.astra_output, self.container, self, pid=pid)
                print("[SatelliteAnalyzer] Opened AbertisAnalyzeScreen")
                self.session.open(MessageBox, _("Abertis analysis in progress, wait a few seconds or press the yellow button to stop."), MessageBox.TYPE_INFO, timeout=5)
                cmd = f'astra --analyze "{option[1]}"'
                print(f"[SatelliteAnalyzer] Executing Abertis command: {cmd}")
                self.container.appClosed.append(self.onAnalyzeFinished)
                self.container.dataAvail.append(self.onDataAvail)
                self.container.execute(cmd)
                print("[SatelliteAnalyzer] Abertis command executed")
            except Exception as e:
                print(f"[SatelliteAnalyzer] Error in onAbertisAnalyzeSelected: {str(e)}")
                self.session.open(MessageBox, f"Error starting Abertis analysis: {str(e)}", MessageBox.TYPE_ERROR)
                self.stopAnalysisCleanup()
        else:
            print("[SatelliteAnalyzer] No PID selected, cancelling Abertis analysis")

    def onDataAvail(self, data):
        try:
            data = data.decode('utf-8')
            for line in data.splitlines():
                print(f"[AstraData]: {line.strip()}")
                if "INFO:" in line:
                    self.astra_output.append(line.strip())
                    if self.astra_analyze_screen:
                        self.astra_analyze_screen.updateResults()
                    if self.abertis_analyze_screen:
                        self.abertis_analyze_screen.updateResults()
        except Exception as e:
            print(f"[SatelliteAnalyzer] Error in onDataAvail: {str(e)}")

    def onAnalyzeFinished(self, retval):
        print(f"[SatelliteAnalyzer] Analysis finished, return code: {retval}, output: {self.astra_output}")
        self.analyzing = False
        if not self.astra_output:
            if self.astra_analyze_screen:
                self.astra_analyze_screen.updateResults()
            if self.abertis_analyze_screen:
                self.abertis_analyze_screen.updateResults()
            self.session.open(MessageBox, _("No results or analysis error."), MessageBox.TYPE_ERROR)
        self.container = None
        os.system("systemctl stop astra-sm")
        print("[SatelliteAnalyzer] Executed systemctl stop astra-sm in onAnalyzeFinished")
        time.sleep(0.5)
        if os.system("pidof astra >/dev/null") == 0:
            print("[SatelliteAnalyzer] Warning: astra process still running after onAnalyzeFinished")
        else:
            print("[SatelliteAnalyzer] astra process successfully terminated in onAnalyzeFinished")
        self.resetTunerAndStream()

    def getCaName(self, caid):
        known = {
            0x0500: "Viaccess",
            0x0600: "Seca Mediaguard",
            0x0900: "NDS Videoguard",
            0x098D: "NDS Videoguard",
            0x098C: "NDS Videoguard",
            0x091F: "NDS Videoguard",
            0x0911: "NDS Videoguard",
            0x09CD: "NDS Videoguard",
            0x09C4: "NDS Videoguard",
            0x0963: "NDS Videoguard",
            0x0961: "NDS Videoguard",
            0x0960: "NDS Videoguard",
            0x092B: "NDS Videoguard",
            0x09BD: "NDS Videoguard",
            0x09F0: "NDS Videoguard",
            0x1813: "Nagravision",
            0x1833: "Nagravision",
            0x1834: "Nagravision",
            0x1830: "Nagravision",
            0x1817: "Nagravision",
            0x1818: "Nagravision",
            0x1878: "Nagravision",
            0x1819: "Nagravision",
            0x1880: "Nagravision",
            0x1883: "Nagravision",
            0x1884: "Nagravision",
            0x1863: "Nagravision",
            0x183D: "Nagravision",
            0x1814: "Nagravision",
            0x1810: "Nagravision",
            0x1811: "Nagravision",
            0x1802: "Nagravision",
            0x1807: "Nagravision",
            0x1843: "Nagravision",
            0x1856: "Nagra Ma",
            0x183E: "Nagra Ma",
            0x1803: "Nagra Ma",
            0x1861: "Nagra Ma",
            0x181D: "Nagra Ma",
            0x186C: "Nagra Ma",
            0x1870: "Nagra Ma",
            0x0E00: "PowerVu",
            0x1700: "Drecrypt",
            0x1800: "Tandberg",
            0x2600: "Biss",
            0x2700: "Bulcrypt",
            0x0D98: "Cryptoworks",
            0x0D97: "Cryptoworks",
            0x0D95: "Cryptoworks",
            0x0D00: "Cryptoworks",
            0x0D01: "Cryptoworks",
            0x0D02: "Cryptoworks",
            0x0D03: "Cryptoworks",
            0x0D04: "Cryptoworks",
            0x0624: "Irdeto",
            0x06E1: "Irdeto",
            0x0653: "Irdeto",
            0x0648: "Irdeto",
            0x06D9: "Irdeto",
            0x0656: "Irdeto",
            0x0650: "Irdeto",
            0x0D96: "Irdeto",
            0x0629: "Irdeto",
            0x0606: "Irdeto",
            0x0664: "Irdeto",
            0x06EE: "Irdeto",
            0x06E2: "Irdeto",
            0x06F8: "Irdeto",
            0x0604: "Irdeto",
            0x069B: "Irdeto",
            0x069F: "Irdeto",
            0x0B01: "Conax",
            0x0B02: "Conax",
            0x0B00: "Conax",
            0x4AEE: "Bulcrypt",
            0x5581: "Bulcrypt",
            0x1EC0: "CryptoGuard",
            0x0100: "Seca/ Mediaguard",
        }
        return known.get(caid, None)

    def getFec(self, fec):
        return {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "4/5", 5: "5/6", 7: "7/8", 8: "8/9", 9: "9/10"}.get(fec, "N/A")

    def getModulation(self, mod):
        return {0: "Auto", 1: "QPSK", 2: "8PSK", 3: "64QAM", 4: "16APSK", 5: "32APSK"}.get(mod, "N/A")

    def getSystem(self, tuner_type, sys):
        if tuner_type == "DVB-S":
            return {0: "DVB-S", 1: "DVB-S2"}.get(sys, "N/A")
        elif tuner_type == "DVB-T":
            return {0: "DVB-T", 1: "DVB-T2"}.get(sys, "N/A")
        elif tuner_type == "DVB-C":
            return {0: "DVB-C", 1: "DVB-C2"}.get(sys, "N/A")
        else:
            return "N/A"

    def getPolarization(self, pol):
        return {0: "H", 1: "V", 2: "L", 3: "R"}.get(pol, "N/A")

    def getBandwidth(self, bw):
        return {6000000: "6 MHz", 7000000: "7 MHz", 8000000: "8 MHz"}.get(bw, f"{bw / 1000000} MHz")

    def getConstellation(self, constellation):
        return {0: "QPSK", 1: "16QAM", 2: "64QAM", 3: "256QAM"}.get(constellation, "N/A")

    def getTransmissionMode(self, mode):
        return {0: "Auto", 1: "2K", 2: "8K", 3: "4K"}.get(mode, "N/A")

    def getGuardInterval(self, gi):
        return {0: "Auto", 1: "1/32", 2: "1/16", 3: "1/8", 4: "1/4"}.get(gi, "N/A")

    def getHierarchy(self, hi):
        return {0: "None", 1: "1", 2: "2", 3: "4", 4: "Auto"}.get(hi, "N/A")

    def getSatelliteNameFromXML(self, orbital_position):
        satellites_file = "/etc/tuxbox/satellites.xml"
        if not os.path.exists(satellites_file):
            return self.formatOrbitalPos(orbital_position)
        try:
            tree = ET.parse(satellites_file)
            root = tree.getroot()
            sat_pos = self.convertOrbitalPos(orbital_position)
            for sat in root.findall("sat"):
                pos = int(sat.get("position", "0"))
                if pos == sat_pos:
                    return sat.get("name", self.formatOrbitalPos(orbital_position))
            return self.formatOrbitalPos(orbital_position)
        except:
            return self.formatOrbitalPos(orbital_position)

    def convertOrbitalPos(self, pos):
        if pos > 1800:
            return pos - 3600
        else:
            return pos

    def formatOrbitalPos(self, pos):
        pos = self.convertOrbitalPos(pos)
        if pos < 0:
            return f"{abs(pos) / 10.0:.1f}W"
        else:
            return f"{pos / 10.0:.1f}E"

    def getBasicInfo(self):
        service = self.session.nav.getCurrentService()
        if not service:
            return "❌ Nema aktivnog servisa."
        info = service.info()
        if not info:
            return "❌ Ne mogu dohvatiti info objekat."
        frontendInfo = service.frontendInfo()
        frontendData = frontendInfo and frontendInfo.getAll(True)
        if not frontendData:
            return "❌ Ne mogu dohvatiti frontend podatke."
        try:
            freq = frontendData.get("frequency", 0) // 1000
        except:
            freq = 0
        try:
            sr = frontendData.get("symbol_rate", 0) // 1000
        except:
            sr = 0
        try:
            fec_inner = frontendData.get("fec_inner", 0)
            fec_str = self.getFec(fec_inner)
        except:
            fec_str = "N/A"
        try:
            pol = frontendData.get("polarization", 0)
            pol_str = self.getPolarization(pol)
        except:
            pol_str = "N/A"
        try:
            orbital_pos = frontendData.get("orbital_position", 0)
            sat_name = self.getSatelliteNameFromXML(orbital_pos)
        except:
            sat_name = "Nepoznat satelit"
        try:
            mod = frontendData.get("modulation", 0)
            mod_str = self.getModulation(mod)
        except:
            mod_str = "N/A"
        try:
            tuner_type = frontendData.get("tuner_type", "")
            system_val = frontendData.get("system", 0)
            system_str = self.getSystem(tuner_type, system_val)
        except:
            system_str = "N/A"
        try:
            pls_mode = frontendData.get("pls_mode", -1)
            pls_mode_str = {0: "Root", 1: "Gold", 2: "Combo"}.get(pls_mode, str(pls_mode))
        except:
            pls_mode_str = "N/A"
        try:
            pls_code = frontendData.get("pls_code", -1)
            pls_code_str = str(pls_code) if pls_code >= 0 else "N/A"
        except:
            pls_code_str = "N/A"
        try:
            t2mi_plp_id = frontendData.get("t2mi_plp_id", -1)
            t2mi_plp_str = str(t2mi_plp_id) if t2mi_plp_id >= 0 else "N/A"
        except:
            t2mi_plp_str = "N/A"
        try:
            t2mi_pid = frontendData.get("t2mi_pid", -1)
            t2mi_pid_str = f"0x{t2mi_pid:X}" if t2mi_pid >= 0 else "N/A"
        except:
            t2mi_pid_str = "N/A"
        try:
            name = info.getName() or "N/A"
        except:
            name = "N/A"
        try:
            provider = info.getInfoString(iServiceInformation.sProvider) or "N/A"
        except:
            provider = "N/A"
        try:
            vpid = info.getInfo(iServiceInformation.sVideoPID)
            vpid_str = f"0x{vpid:X}" if vpid != -1 else "N/A"
        except:
            vpid_str = "N/A"
        try:
            apid = info.getInfo(iServiceInformation.sAudioPID)
            apid_str = f"0x{apid:X}" if apid != -1 else "N/A"
        except:
            apid_str = "N/A"
        try:
            pcrpid = info.getInfo(iServiceInformation.sPCRPID)
            pcr_str = f"0x{pcrpid:X}" if pcrpid != -1 else "N/A"
        except:
            pcr_str = "N/A"
        try:
            pmtpid = info.getInfo(iServiceInformation.sPMTPID)
            pmt_str = f"0x{pmtpid:X}" if pmtpid != -1 else "N/A"
        except:
            pmt_str = "N/A"
        try:
            txt_pid = info.getInfo(iServiceInformation.sTXTPID)
            txt_str = f"0x{txt_pid:X}" if txt_pid != -1 else "N/A"
        except:
            txt_str = "N/A"
        dvbt_params = ""
        if tuner_type in ["DVB-T", "DVB-T2"]:
            try:
                bandwidth = frontendData.get("bandwidth", 0)
                bandwidth_str = self.getBandwidth(bandwidth)
            except:
                bandwidth_str = "N/A"
            try:
                code_rate_hp = frontendData.get("code_rate_hp", 0)
                code_rate_hp_str = self.getFec(code_rate_hp)
            except:
                code_rate_hp_str = "N/A"
            try:
                code_rate_lp = frontendData.get("code_rate_lp", 0)
                code_rate_lp_str = self.getFec(code_rate_lp)
            except:
                code_rate_lp_str = "N/A"
            try:
                constellation = frontendData.get("constellation", 0)
                constellation_str = self.getConstellation(constellation)
            except:
                constellation_str = "N/A"
            try:
                transmission_mode = frontendData.get("transmission_mode", 0)
                transmission_mode_str = self.getTransmissionMode(transmission_mode)
            except:
                transmission_mode_str = "N/A"
            try:
                guard_interval = frontendData.get("guard_interval", 0)
                guard_interval_str = self.getGuardInterval(guard_interval)
            except:
                guard_interval_str = "N/A"
            try:
                hierarchy = frontendData.get("hierarchy_information", 0)
                hierarchy_str = self.getHierarchy(hierarchy)
            except:
                hierarchy_str = "N/A"
            dvbt_params = f"""
       Bandwidth: {bandwidth_str}
       Code Rate HP: {code_rate_hp_str}
       Code Rate LP: {code_rate_lp_str}
       Constellation: {constellation_str}
       Transmission Mode: {transmission_mode_str}
       Guard Interval: {guard_interval_str}
       Hierarchy: {hierarchy_str}
            """
        text = f"""
       Channel: {name}
       Provider: {provider}
       Satellite: {sat_name}
       Frequency: {freq} MHz
       Polarization: {pol_str}
       Symbol Rate: {sr}k
       FEC: {fec_str}
       Modulation: {mod_str}
       SYSTEM: {system_str}
       PLS MODE: {pls_mode_str}
       PLS CODE: {pls_code_str}
       T2MI PLP ID: {t2mi_plp_str}
       T2MI PID: {t2mi_pid_str}
    {dvbt_params}
       VIDEO PID: {vpid_str}
       AUDIO PID: {apid_str}
       PCR PID: {pcr_str}
       PMT PID: {pmt_str}
       TELETEXT PID: {txt_str}
        """.strip()
        return text

    def getAdvancedInfo(self):
        service = self.session.nav.getCurrentService()
        if not service:
            return "No active service."
        info = service.info()
        if not info:
            return "Cannot retrieve info object."
        service_ref = self.getServiceReference()
        try:
            caids = info.getInfoObject(iServiceInformation.sCAIDs) or []
        except:
            caids = []
        active_caid = None
        ecm_path = "/tmp/ecm.info"
        if os.path.exists(ecm_path):
            try:
                with open(ecm_path, 'r') as f:
                    for line in f:
                        if line.startswith("caid:"):
                            caid_str = line.split(":")[1].strip().replace("0x", "")
                            try:
                                active_caid = int(caid_str, 16)
                                break
                            except:
                                pass
            except:
                pass
        caid_list = []
        if caids:
            for caid in sorted(set(caids)):
                name = self.getCaName(caid)
                marker = "Active" if caid == active_caid else ""
                if name:
                    caid_list.append(f"   {name} (0x{caid:04X}) {marker}")
                else:
                    caid_list.append(f"   CAID: 0x{caid:04X} {marker}")
        else:
            caid_list.append("No encryption")
        frontendInfo = service.frontendInfo()
        frontendData = frontendInfo and frontendInfo.getAll(True)
        try:
            snr_db = frontendData.get("tuner_signal_quality_db", 0) / 100.0
            snr_percent = frontendData.get("tuner_signal_quality", 0) // 655
            ber = frontendData.get("tuner_bit_error_rate", 0)
            agc = frontendData.get("tuner_signal_power", 0) // 655
        except:
            snr_db, snr_percent, ber, agc = 0.0, 0, 0, 0
        try:
            sid = info.getInfo(iServiceInformation.sSID)
        except:
            sid = -1
        try:
            tsid = info.getInfo(iServiceInformation.sTSID)
        except:
            tsid = -1
        try:
            onid = info.getInfo(iServiceInformation.sONID)
        except:
            onid = -1
        right_text = [
            "Encryption:",
            *caid_list,
            "",
            "SIGNAL INFO:",
            f"   Strength: {snr_percent} %",
            f"   SNR: {snr_db:.2f} dB",
            f"   BER: {ber if ber != 0 else 'N/A'}",
            f"   AGC: {agc if agc != 0 else 'N/A'}",
            "",
            "SI / TS / ONID:",
            f"   SID: 0x{sid:04X}",
            f"   TSID: 0x{tsid:04X}",
            f"   ONID: 0x{onid:04X}",
            "",
            "Service Reference:",
            f"   {service_ref}"
        ]
        return "\n".join(right_text)

    def parse_astra_conf(self, conf_path="/etc/astra/astra.conf"):
        import re, os
        if not os.path.exists(conf_path):
            print(f"[parse_astra_conf] File not found: {conf_path}")
            return {"t2mi": {}, "abertis": {}}
        with open(conf_path, "r") as f:
            conf_content = f.read()
        
        # T2MI blokovi
        t2mi_blocks = re.findall(
            r'(\w+)\s*=\s*make_t2mi_decap\(\{([^}]*)\}\)',
            conf_content, re.DOTALL | re.IGNORECASE
        )
        print(f"[parse_astra_conf] Found {len(t2mi_blocks)} t2mi_decap blocks")
        result = {"t2mi": {}, "abertis": {}}
        for var_name, body in t2mi_blocks:
            pid = re.search(r'pid\s*=\s*(\d+)', body)
            name = re.search(r'name\s*=\s*"([^"]+)"', body)
            result["t2mi"][var_name] = {
                "pid": pid.group(1) if pid else None,
                "name": name.group(1) if name else var_name,
                "output": None
            }
            print(f"[parse_astra_conf] Added T2MI block var={var_name} pid={result['t2mi'][var_name]['pid']} name={result['t2mi'][var_name]['name']}")

        # Abertis i T2MI channel blokovi
        channel_blocks = re.findall(
            r'make_channel\(\{(.*?)\}\)',
            conf_content, re.DOTALL | re.IGNORECASE
        )
        print(f"[parse_astra_conf] Found {len(channel_blocks)} make_channel blocks")
        for body in channel_blocks:
            name_match = re.search(r'name\s*=\s*"([^"]+)"', body)
            input_match = re.search(r'input\s*=\s*\{[^"]*"([^"]+)"', body, re.DOTALL)
            output_match = re.search(r'output\s*=\s*\{[^"]*"([^"]+)"', body, re.DOTALL)
            transform_match = re.search(r'transform\s*=\s*\{\{[^}]*format\s*=\s*"pipe"', body, re.DOTALL)
            is_abertis = transform_match and "abertis" in output_match.group(1).lower() if output_match and transform_match else False
            name = name_match.group(1) if name_match else "Unknown"
            if input_match and output_match:
                ref = input_match.group(1).split("/")[-1].replace(":", "")
                output_url = output_match.group(1)
                if is_abertis:
                    pid_match = re.search(r'pid(\d+)', output_url)
                    pid = pid_match.group(1) if pid_match else None
                    result["abertis"][ref] = {
                        "pid": pid,
                        "name": name,
                        "output": output_url
                    }
                    print(f"[parse_astra_conf] Added Abertis block ref={ref} pid={pid} name={name} -> {output_url}")
                else:
                    for t2mi_ref, t2mi_data in result["t2mi"].items():
                        if t2mi_ref in input_match.group(1):
                            t2mi_data["output"] = output_url
                            print(f"[parse_astra_conf] Linked T2MI {t2mi_ref} -> {output_url}")
            else:
                print(f"[parse_astra_conf] Found input but no output in block: {body[:50]}...")
        return result

    def createBouquet(self):
        print("[SatelliteAnalyzer] Starting bouquet creation")
        log_dir = "/tmp/CiefpSatelliteAnalyzer"
        if not os.path.exists(log_dir):
            self.session.open(MessageBox, _("Log directory not found!"), MessageBox.TYPE_ERROR)
            return
        logs = [f for f in os.listdir(log_dir) if f.endswith(".log")]
        if not logs:
            self.session.open(MessageBox, _("No log files found!"), MessageBox.TYPE_ERROR)
            return
        choices = []
        for log in sorted(logs):
            log_type = "Abertis" if "abertis_analyze" in log else "T2MI"
            choices.append((f"{log} ({log_type})", (log, log_type)))
        self.session.openWithCallback(
            self.logSelected,
            ChoiceBox,
            title="Select analyze log file",
            list=choices
        )

    def logSelected(self, choice):
        if not choice:
            return
        log_file, log_type = choice[1]
        self.selected_log_file = log_file
        print(f"[SatelliteAnalyzer] User selected log: {log_file} ({log_type})")
        blocks = self.parse_astra_conf()
        if not blocks[log_type.lower()]:
            self.session.open(MessageBox, _(f"No {log_type} blocks found in astra.conf!"), MessageBox.TYPE_ERROR)
            return
        choices = []
        for ref, data in blocks[log_type.lower()].items():
            if data["output"]:
                label = f"{data['name']} (pid {data['pid']}) -> {data['output']}"
                choices.append((label, ref))
        if not choices:
            self.session.open(MessageBox, _(f"No usable {log_type} blocks with output found!"), MessageBox.TYPE_ERROR)
            return
        self.session.openWithCallback(
            self.blockSelected,
            ChoiceBox,
            title=f"Select {log_type} block from astra.conf",
            list=choices
        )

    def blockSelected(self, choice):
        if not choice:
            return
        block_ref = choice[1]
        log_file = self.selected_log_file
        print(f"[SatelliteAnalyzer] User selected block: {block_ref} for log {log_file}")
        self.processSelectedLog(log_file, block_ref)

    def processSelectedLog(self, log_file, block_ref):
        import re, os
        from urllib.parse import quote, unquote
        from enigma import eDVBDB
        log_path = os.path.join("/tmp/CiefpSatelliteAnalyzer", log_file)
        if not os.path.exists(log_path):
            self.session.open(MessageBox, _("Selected log file not found!"), MessageBox.TYPE_ERROR)
            return
        blocks = self.parse_astra_conf()
        log_type = "abertis" if "abertis_analyze" in log_file else "t2mi"
        if block_ref not in blocks[log_type] or not blocks[log_type][block_ref]["output"]:
            self.session.open(MessageBox, _(f"Selected {log_type} block not found in astra.conf!"),
                              MessageBox.TYPE_ERROR)
            return
        matched = blocks[log_type][block_ref]
        base_url = matched["output"]
        marker_pid = matched["pid"]
        print(f"[SatelliteAnalyzer] Using block {block_ref}: pid={marker_pid}, url={base_url}")

        # Dohvati informaciju o satelitu i frekvenciji
        satellite = "Unknown"
        frequency = 0
        service = self.session.nav.getCurrentService()
        if service:
            frontendInfo = service.frontendInfo()
            if frontendInfo:
                frontendData = frontendInfo.getAll(True)
                if frontendData:
                    try:
                        orbital_pos = frontendData.get("orbital_position", 0)
                        satellite = self.formatOrbitalPos(orbital_pos)
                        frequency = frontendData.get("frequency", 0) // 1000  # Frekvencija u MHz
                    except Exception as e:
                        print(f"[SatelliteAnalyzer] Error getting satellite info: {str(e)}")
                        satellite = "Unknown"
                        frequency = 0

        # Parsiraj log fajl i prikupi kanale
        new_channels = []
        sid = service = provider = None
        with open(log_path, "r") as f:
            for line in f:
                if 'sid:' in line:
                    sid = re.search(r'sid:\s*(\d+)', line)
                    if sid:
                        sid = sid.group(1)
                elif 'Service:' in line:
                    service = re.search(r'Service:\s*(.+)', line)
                    if service:
                        service = service.group(1).strip()
                elif 'Provider:' in line and sid and service:
                    provider_match = re.search(r'Provider:\s*(.*)', line)
                    provider = provider_match.group(1).strip() if provider_match and provider_match.group(
                        1).strip() else "RTVE"
                    # Proširena heuristika za detekciju radio kanala
                    radio_keywords = ["Radio", "RNE", "FM", "AM", "Cadena", "SER", "Onda Cero", "COPE"]
                    is_radio = any(keyword in service for keyword in radio_keywords)
                    channel_type = "RADIO" if is_radio else "TV"
                    # Loguj kanale koji nisu jasno klasifikovani kao radio
                    if not is_radio and not ("TV" in service or "HD" in service):
                        print(
                            f"[SatelliteAnalyzer] Warning: Channel '{service}' classified as TV by default (no clear radio indicator)")
                    new_channels.append({
                        'sid': int(sid),
                        'name': service,
                        'provider': provider,
                        'type': channel_type,
                        'pid': marker_pid,
                        'url': base_url
                    })
                    sid = service = provider = None

        if not new_channels:
            self.session.open(MessageBox, _("No channels found in selected log!"), MessageBox.TYPE_ERROR)
            return

        # Učitaj postojeće kanale iz buketa
        bouquet_path = '/etc/enigma2/userbouquet.buket_t2mi.tv' if log_type == "t2mi" else '/etc/enigma2/userbouquet.buket_abertis.tv'
        existing_channels = []
        existing_content = ""
        if os.path.exists(bouquet_path):
            with open(bouquet_path, 'r') as f:
                existing_content = f.read()
            # Parsiraj postojeće kanale
            lines = existing_content.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if '#SERVICE' in line and '#####' not in line:
                    # Fleksibilniji regex za rukovanje varijacijama u formatu
                    service_match = re.search(
                        r'#SERVICE 1:0:([12]):([0-9A-F]+):([0-9A-F]+):([0-9A-F]+):0:0:0:0:(.*?):(.+)', line)
                    if service_match:
                        service_type, sid_hex, tsid, onid, url, name = service_match.groups()
                        # Očisti višestruke PID-ove i tip iz imena (npr. (TV) La 1 HD (2025) -> La 1 HD)
                        clean_name = re.sub(r'^\s*\((?:TV|RADIO)\)\s*|\s*\(\d+\)(?:\s*\(\d+\))*\s*$', '', name).strip()
                        # Pokušaj izvući PID iz imena kanala
                        pid_match = re.search(r'\((\d+)\)$', name)
                        pid = pid_match.group(1) if pid_match else "Unknown"
                        # Pokušaj izvući tip iz imena kanala ili na osnovu service_type
                        type_match = re.search(r'^\((TV|RADIO)\)\s*', name)
                        channel_type = type_match.group(1) if type_match else ("RADIO" if service_type == "2" else "TV")
                        # Dekodiraj URL kako bismo izbegli višestruko enkodiranje
                        url = unquote(url)
                        existing_channels.append({
                            'sid': int(sid_hex, 16),
                            'tsid': tsid,
                            'onid': onid,
                            'url': url,
                            'name': clean_name,
                            'type': channel_type,
                            'pid': pid
                        })
                    else:
                        print(f"[SatelliteAnalyzer] Warning: Skipping invalid SERVICE line: {line}")
                i += 1

        # Kombinuj nove kanale sa postojećim, ažuriraj tip ako je potrebno
        all_channels = []
        existing_keys = {(ch['sid'], ch['tsid'], ch['onid'], ch['url'], ch['name']) for ch in existing_channels}
        for ch in new_channels:
            key = (ch['sid'], format(frequency, 'X') if frequency else '2DE3', format(int(ch['pid']), 'X'), ch['url'],
                   ch['name'])
            # Ako kanal već postoji, ažuriraj njegov tip i PID
            for existing_ch in existing_channels:
                if (existing_ch['sid'], existing_ch['tsid'], existing_ch['onid'], existing_ch['url'],
                    existing_ch['name']) == key:
                    existing_ch['type'] = ch['type']  # Ažuriraj tip (TV/RADIO)
                    existing_ch['pid'] = ch['pid']  # Ažuriraj PID ako je potrebno
                    break
            else:
                # Ako kanal nije pronađen, dodaj ga kao nov
                all_channels.append({
                    'sid': ch['sid'],
                    'tsid': format(frequency, 'X') if frequency else '2DE3',
                    'onid': format(int(ch['pid']), 'X'),
                    'url': ch['url'],
                    'name': ch['name'],
                    'type': ch['type'],
                    'pid': ch['pid']
                })
        # Dodaj sve postojeće kanale u all_channels
        all_channels.extend(existing_channels)

        # Sortiraj kanale po PID-u, pa po SID-u radi konzistentnosti
        all_channels.sort(key=lambda x: (x['pid'], x['sid']))

        # Generiši sadržaj buketa grupisan po PID-ovima
        tsid = format(frequency, 'X') if frequency else '2DE3'  # TSID je frekvencija u hex
        namespace = '300000'
        content = '#NAME ##( Abertis DTT Sat )##\n'

        # Grupisanje kanala po PID-u
        from collections import defaultdict
        channels_by_pid = defaultdict(list)
        for ch in all_channels:
            channels_by_pid[ch['pid']].append(ch)

        # Generiši linije za svaki PID
        for pid in sorted(channels_by_pid.keys()):
            if pid == "Unknown":
                continue  # Preskoči kanale bez poznatog PID-a
            content += f'#SERVICE 1:64:{pid}:0:0:0:0:0:0:0::##### Abertis PID {pid} #####\n'
            content += f'#DESCRIPTION ##### Abertis PID {pid} #####\n'
            for ch in channels_by_pid[pid]:
                sid_hex = format(ch['sid'], 'X')
                # Koristi 1 za TV, 2 za RADIO
                service_type = "2" if ch["type"] == "RADIO" else "1"
                service_line = f'#SERVICE 1:0:{service_type}:{sid_hex}:{ch["tsid"]}:{ch["onid"]}:0:0:0:0:{quote(unquote(ch["url"]), safe="/")}:({ch["type"]}) {ch["name"]} ({ch["pid"]})\n'
                desc_line = f'#DESCRIPTION ({ch["type"]}) {ch["name"]} ({ch["pid"]})\n'
                content += service_line + desc_line

        # Upis u buket
        with open(bouquet_path, 'w') as f:
            f.write(content)
        print(f"[SatelliteAnalyzer] Created/updated {log_type} bouquet file")

        # Ažuriraj bouquets.tv
        bouquets_tv_path = '/etc/enigma2/bouquets.tv'
        bouquet_name = 'userbouquet.buket_abertis.tv' if log_type == "abertis" else 'userbouquet.buket_t2mi.tv'
        add_line = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bouquet_name}" ORDER BY bouquet\n'
        if os.path.exists(bouquets_tv_path):
            with open(bouquets_tv_path, 'r') as f:
                bouquets_data = f.read()
            if add_line not in bouquets_data:
                with open(bouquets_tv_path, 'a') as f:
                    f.write(add_line)
                print(f"[SatelliteAnalyzer] Added {log_type} bouquet reference to bouquets.tv")

        # Osveži bukete
        eDVBDB.getInstance().reloadBouquets()
        self.session.openWithCallback(
            lambda x: None,  # Callback koji ne radi ništa
            MessageBox,
            _(f"{log_type.capitalize()} bouquet created/updated and reloaded successfully!"),
            MessageBox.TYPE_INFO,
            timeout=5,
            default=True
        )