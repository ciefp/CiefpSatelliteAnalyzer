from enigma import eServiceCenter, eServiceReference, iServiceInformation, eTimer, eConsoleAppContainer
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Screens.InputBox import InputBox
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Sources.List import List
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap
from Components.ProgressBar import ProgressBar
from Components.Button import Button
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Screens.Setup import Setup
from Components.config import config, ConfigText, ConfigInteger, ConfigSelection
import os
from enigma import eDVBDB
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

            # Novi format naziva za T2MI
            base_filename = f"t2mi_{provider}_{satellite}_{date_str}_{pid_str}.log"
            counter = 1
            filename = os.path.join(dir_path, base_filename)

            # Proveri da li fajl već postoji i dodaj redni broj
            while os.path.exists(filename):
                base_name = f"t2mi_{counter}_{provider}_{satellite}_{date_str}_{pid_str}.log"
                filename = os.path.join(dir_path, base_name)
                counter += 1

            with open(filename, 'w') as f:
                f.write("\n".join(self.analyze_output))
            self.session.open(MessageBox, f"Results saved to:\n{filename}", MessageBox.TYPE_INFO, timeout=5)
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

            # Novi format naziva za Abertis
            base_filename = f"abertis_{provider}_{satellite}_{date_str}_{pid_str}.log"
            counter = 1
            filename = os.path.join(dir_path, base_filename)

            # Proveri da li fajl već postoji i dodaj redni broj
            while os.path.exists(filename):
                base_name = f"abertis_{counter}_{provider}_{satellite}_{date_str}_{pid_str}.log"
                filename = os.path.join(dir_path, base_name)
                counter += 1

            with open(filename, 'w') as f:
                f.write("\n".join(self.analyze_output))
            self.session.open(MessageBox, f"Results saved to:\n{filename}", MessageBox.TYPE_INFO, timeout=5)
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


class T2MIDecapConfigScreen(Screen):
    skin = """
    <screen name="T2MIDecapConfigScreen" position="center,center" size="1800,900" title="..:: Add T2MI Decap Block ::..">
        <eLabel position="0,0" size="1800,900" backgroundColor="#0D1B36" zPosition="-1" />
        <widget source="Title" render="Label" position="20,20" size="1760,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" />

        <!-- Tabela sa poljima -->
        <widget name="config" position="50,100" size="1700,600" 
                font="Regular;24" transparent="1" foregroundColor="white" />

        <!-- Status bar -->
        <widget name="status" position="50,720" size="1700,30" 
                font="Regular;20" halign="center" foregroundColor="yellow" />

        <!-- Dugmad -->
        <widget name="key_red" position="100,780" size="320,40" 
                backgroundColor="red" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_green" position="500,780" size="320,40" 
                backgroundColor="green" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_yellow" position="900,780" size="320,40" 
                backgroundColor="yellow" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_blue" position="1300,780" size="320,40" 
                backgroundColor="blue" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, parent):
        Screen.__init__(self, session)
        self.parent = parent
        self.config_list = []
        self["config"] = ScrollLabel("")
        self["status"] = Label(_("Fill in the fields and navigate with arrow keys"))
        self["key_red"] = Button(_("Exit"))
        self["key_green"] = Button(_("OK"))
        self["key_yellow"] = Button(_("Preview"))
        self["key_blue"] = Button(_("Save to astra.conf"))

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
                                    {
                                        "ok": self.keyOK,
                                        "cancel": self.keyCancel,
                                        "red": self.keyCancel,
                                        "green": self.keyOK,
                                        "yellow": self.previewConfig,
                                        "blue": self.saveConfig,
                                        "up": self.keyUp,
                                        "down": self.keyDown,
                                        "left": self.keyLeft,
                                        "right": self.keyRight,
                                    }, -2)

        # Predefinisane vrednosti
        self.plp_options = ["0", "1", "2"]
        self.pnr_options = ["0"]
        self.pid_options = ["4095", "4096", "4097", "custom_pid"]

        # Trenutni kanal info
        self.current_service_ref = self.parent.getServiceReference()
        self.current_channel_name = self.getCurrentChannelName()

        # Inicijalne vrednosti - ISPRAVLJENO: localhost -> 127.0.0.1
        self.current_values = {
            'header': '',  # NOVO POLJE ZA ZAGLAVLJE
            'decap_name': 't2mi_dasto_plp0',
            'channel_name': self.current_channel_name,
            'input_url': f'http://127.0.0.1:8001/{self.current_service_ref}',  # ISPRAVLJENO
            'plp': '0',
            'pnr': '0',
            'pid': '4095',
            'custom_pid': '',
            'output_path': 'dastoplp0'
        }

        self.current_field = 0
        self.fields = [
            {'name': 'Add Header', 'key': 'header', 'type': 'text'},  # NOVO POLJE
            {'name': 'Decap variable name', 'key': 'decap_name', 'type': 'text'},
            {'name': 'Channel name', 'key': 'channel_name', 'type': 'text'},
            {'name': 'Input URL', 'key': 'input_url', 'type': 'text'},
            {'name': 'PLP', 'key': 'plp', 'type': 'options', 'options': self.plp_options},
            {'name': 'PNR', 'key': 'pnr', 'type': 'options', 'options': self.pnr_options},
            {'name': 'PID', 'key': 'pid', 'type': 'options', 'options': self.pid_options},
            {'name': 'Custom PID', 'key': 'custom_pid', 'type': 'text'},
            {'name': 'Output path', 'key': 'output_path', 'type': 'text'}
        ]

        self.updateDisplay()

    def getCurrentChannelName(self):
        """Dobijanje naziva trenutnog kanala"""
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            if info:
                name = info.getName()
                if name:
                    return name
        return "Unknown Channel"

    def updateDisplay(self):
        """Ažuriranje prikaza tabele"""
        display_text = ""
        for i, field in enumerate(self.fields):
            value = self.current_values[field['key']]
            marker = " > " if i == self.current_field else "   "

            if field['type'] == 'options':
                display_text += f"{marker}{field['name']}: [{value}]\n"
            else:
                display_text += f"{marker}{field['name']}: {value}\n"

        self["config"].setText(display_text)

    def keyOK(self):
        """Enter dugme za editovanje polja"""
        current_field = self.fields[self.current_field]

        if current_field['type'] == 'text':
            # Otvori virtualnu tastaturu za unos teksta
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(
                self.textEntered,
                VirtualKeyBoard,
                title=_(f"Enter {current_field['name']}"),
                text=self.current_values[current_field['key']]
            )
        elif current_field['type'] == 'options':
            # Prikaži opcije u ChoiceBox-u
            choices = [(opt, opt) for opt in current_field['options']]
            self.session.openWithCallback(
                self.optionSelected,
                ChoiceBox,
                title=_(f"Select {current_field['name']}"),
                list=choices
            )

    def textEntered(self, result):
        """Callback za unos teksta"""
        if result:
            current_field = self.fields[self.current_field]

            # Ako je input_url polje, automatski zameni localhost sa 127.0.0.1
            if current_field['key'] == 'input_url':
                result = result.replace('localhost', '127.0.0.1')

            self.current_values[current_field['key']] = result
            self.updateDisplay()

    def optionSelected(self, result):
        """Callback za izbor opcije"""
        if result:
            current_field = self.fields[self.current_field]
            self.current_values[current_field['key']] = result[1]

            # Ako je izabran custom_pid, prikaži custom polje
            if current_field['key'] == 'pid' and result[1] == 'custom_pid':
                # Pomeri se na custom_pid polje
                self.current_field = 6  # Index custom_pid polja
            elif current_field['key'] == 'pid' and result[1] != 'custom_pid':
                # Reset custom_pid ako nije izabran custom
                self.current_values['custom_pid'] = ''

            self.updateDisplay()

    def keyUp(self):
        """Strelica gore"""
        if self.current_field > 0:
            self.current_field -= 1
            self.updateDisplay()

    def keyDown(self):
        """Strelica dole"""
        if self.current_field < len(self.fields) - 1:
            self.current_field += 1
            self.updateDisplay()

    def keyLeft(self):
        """Strelica levo - za opcije"""
        current_field = self.fields[self.current_field]
        if current_field['type'] == 'options':
            current_value = self.current_values[current_field['key']]
            options = current_field['options']
            current_index = options.index(current_value) if current_value in options else 0
            new_index = (current_index - 1) % len(options)
            self.current_values[current_field['key']] = options[new_index]

            # Ako je PID promenjen
            if current_field['key'] == 'pid':
                if options[new_index] != 'custom_pid':
                    self.current_values['custom_pid'] = ''

            self.updateDisplay()

    def keyRight(self):
        """Strelica desno - za opcije"""
        current_field = self.fields[self.current_field]
        if current_field['type'] == 'options':
            current_value = self.current_values[current_field['key']]
            options = current_field['options']
            current_index = options.index(current_value) if current_value in options else 0
            new_index = (current_index + 1) % len(options)
            self.current_values[current_field['key']] = options[new_index]

            # Ako je PID promenjen
            if current_field['key'] == 'pid':
                if options[new_index] != 'custom_pid':
                    self.current_values['custom_pid'] = ''

            self.updateDisplay()

    def previewConfig(self):
        """Prikaz konfiguracije pre čuvanja"""
        config_text = self.generateConfig()
        self.session.open(MessageBox, config_text, MessageBox.TYPE_INFO, timeout=30)

    def generateConfig(self):
        """Generisanje koda za astra.conf - LEPŠE FORMATIRANJE"""
        # Automatski zameni localhost sa 127.0.0.1 u input URL-u
        input_url = self.current_values['input_url'].replace('localhost', '127.0.0.1')

        # Koristi custom_pid ako je izabran, inače koristi izabrani PID
        pid_value = self.current_values['custom_pid'] if self.current_values['pid'] == 'custom_pid' else \
        self.current_values['pid']

        # Dodaj header ako je unet
        header_text = ""
        if self.current_values['header']:
            header_text = f"-- {self.current_values['header']}\n\n"

        # LEPŠE FORMATIRANJE sa 4 spaces umesto 2
        config = f"""{header_text}{self.current_values['decap_name']} = make_t2mi_decap({{
        name = "{self.current_values['channel_name']}",
        input = "{input_url}",
        plp = {self.current_values['plp']},
        pnr = {self.current_values['pnr']},
        pid = {pid_value},
    }})

    make_channel({{
        name = "{self.current_values['channel_name']}",
        input = {{ "t2mi://{self.current_values['decap_name']}", }},
        output = {{ "http://0.0.0.0:9999/{self.current_values['output_path']}", }},
    }})
    """
        return config

    def saveConfig(self):
        """Čuvanje konfiguracije u astra.conf - SA REBOOT UPRAZORENJEM"""
        try:
            config_text = self.generateConfig()
            conf_path = "/etc/astra/astra.conf"

            # Proveri da li direktorijum postoji
            os.makedirs(os.path.dirname(conf_path), exist_ok=True)

            # Dodaj u fajl (append mode)
            with open(conf_path, "a") as f:
                f.write("\n" + config_text)

            # PITAJ KORISNIKA DA LI ŽELI REBOOT
            message = _("✅ Configuration saved to astra.conf!\n\n") + \
                      _("⚠️  FULL SYSTEM REBOOT REQUIRED  ⚠️\n\n") + \
                      _("Astra-SM will load the new configuration only after system reboot.\n\n") + \
                      _("Do you want to reboot now?")

            self.session.openWithCallback(
                self.rebootAfterSave,
                MessageBox,
                message,
                MessageBox.TYPE_YESNO
            )

        except Exception as e:
            self.session.open(MessageBox, _("Error saving configuration: ") + str(e), MessageBox.TYPE_ERROR)

    def rebootAfterSave(self, result):
        """Callback za reboot nakon čuvanja"""
        if result:
            # Snimi poruku pre rebota
            self.session.open(
                MessageBox,
                _("System will now reboot...\nPlease wait 2-3 minutes for full restart."),
                MessageBox.TYPE_INFO,
                timeout=5
            )
            # Automatski reboot
            import os
            os.system("reboot")
        else:
            # Prikaži uputstvo za manual reboot
            self.session.open(
                MessageBox,
                _("Remember to reboot system manually!\n\nGo to: Astra.conf menu → Reboot system"),
                MessageBox.TYPE_INFO,
                timeout=10
            )
            self.close()

    def keyCancel(self):
        self.close()

class AstraConfViewScreen(Screen):
    skin = """
    <screen name="AstraConfViewScreen" position="center,center" size="1800,900" title="..:: astra.conf Viewer ::..">
        <!-- Pozadina -->
        <eLabel position="0,0" size="1400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <!-- Pozadina desno -->
        <eLabel position="1400,500" size="400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <widget name="background2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/background.png" position="1400,0" size="400,500" />

        <!-- Sadržaj astra.conf - ORIJENTISAN NA LEVO -->
        <widget name="conf_content" position="20,20" size="1360,860" 
                font="Console;18" transparent="1" foregroundColor="white" />

        <!-- Naslov -->
        <widget source="Title" render="Label" position="1400,520" size="400,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" backgroundColor="#0D1B36" />

        <!-- Dugmad -->
        <widget name="key_red" position="1440,600" size="320,40" 
                backgroundColor="red" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_green" position="1440,660" size="320,40" 
                backgroundColor="green" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_yellow" position="1440,720" size="320,40" 
                backgroundColor="yellow" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, content):
        Screen.__init__(self, session)
        self.content = content
        self["conf_content"] = ScrollLabel("")
        self["background2"] = Pixmap()
        self["key_red"] = Button(_("Close"))
        self["key_green"] = Button(_("Edit"))
        self["key_yellow"] = Button(_("Save As"))

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
                                    {
                                        "ok": self.close,
                                        "cancel": self.close,
                                        "red": self.close,
                                        "green": self.editConf,
                                        "yellow": self.saveAs,
                                        "up": self["conf_content"].pageUp,
                                        "down": self["conf_content"].pageDown,
                                        "left": self["conf_content"].pageUp,
                                        "right": self["conf_content"].pageDown,
                                    }, -2)

        self.onLayoutFinish.append(self.showContent)

    def showContent(self):
        """Prikaz sadržaja astra.conf"""
        self["conf_content"].setText(self.content)

    def editConf(self):
        """Editovanje astra.conf"""
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self.confEdited,
            VirtualKeyBoard,
            title=_("Edit astra.conf"),
            text=self.content
        )

    def confEdited(self, result):
        """Callback nakon editovanja"""
        if result:
            try:
                conf_path = "/etc/astra/astra.conf"
                with open(conf_path, "w") as f:
                    f.write(result)
                self.content = result
                self["conf_content"].setText(self.content)
                self.session.open(MessageBox, _("astra.conf updated!"), MessageBox.TYPE_INFO)
            except Exception as e:
                self.session.open(MessageBox, _("Error saving astra.conf: ") + str(e), MessageBox.TYPE_ERROR)

    def saveAs(self):
        """Čuvanje kopije astra.conf"""
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self.saveAsCallback,
            VirtualKeyBoard,
            title=_("Save as (enter filename)"),
            text="astra_backup.conf"
        )

    def saveAsCallback(self, result):
        """Callback za čuvanje kopije"""
        if result:
            try:
                backup_path = f"/etc/astra/{result}"
                with open(backup_path, "w") as f:
                    f.write(self.content)
                self.session.open(MessageBox, _("Backup saved as: ") + result, MessageBox.TYPE_INFO)
            except Exception as e:
                self.session.open(MessageBox, _("Error saving backup: ") + str(e), MessageBox.TYPE_ERROR)


class DataBrowserScreen(Screen):
    skin = """
    <screen name="DataBrowserScreen" position="center,center" size="1800,900" title="..:: Data Browser ::..">
        <eLabel position="0,0" size="1800,900" backgroundColor="#0D1B36" zPosition="-1" />
        
        <widget name="list" position="40,60" size="1720,720" scrollbarMode="showOnDemand"
                foregroundColor="#ffffff" backgroundColor="#1a1a1a" font="Console;24" />

        <widget name="status" position="40,790" size="1720,40" font="Regular;22"
                foregroundColor="#BBBBBB" halign="left" valign="center" transparent="1" />

        <widget name="key_red" position="120,840" size="320,40" backgroundColor="red"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_green" position="520,840" size="320,40" backgroundColor="green"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_yellow" position="920,840" size="320,40" backgroundColor="yellow"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_blue" position="1320,840" size="320,40" backgroundColor="blue"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, parent, orbital_pos):
        Screen.__init__(self, session)
        self.parent = parent
        self.orbital_pos = int(orbital_pos or 0)

        self["list"] = MenuList([])
        self["status"] = Label("Loading...")
        self["key_red"]    = Button("Cancel")
        self["key_green"]  = Button("OK Edit")       # ili nešto drugo ako koristiš green
        self["key_yellow"] = Button("Add Fake T2MI")
        self["key_blue"]   = Button("Reload DB")  # opciono

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "ok": self.openLamedbEditor,
                "up": self["list"].up,
                "down": self["list"].down,
                "left": self["list"].pageUp,
                "right": self["list"].pageDown,
                "red": self.close,
                "green": self.openLamedbEditor,
                "yellow": self.addFakeT2MI,
            },
            -2
        )

        self.onLayoutFinish.append(self.reload)
    REF_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{8}:[0-9a-fA-F]{4}:[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]+:0$")

    def _find_ref_index(self, items, start_idx):
        i = start_idx
        while i >= 0:
            s = (items[i] or "").strip()
            if self.REF_RE.match(s):
                return i
            i -= 1
        return None

    def _extract_service_entry_from_list(self, selected_idx):
        items = getattr(self, "formatted_items", None)
        if not items:
            print("[DataBrowser] formatted_items is None or empty")
            return None

        if selected_idx < 0 or selected_idx >= len(items):
            print("[DataBrowser] Invalid selected index:", selected_idx)
            return None

        line = (items[selected_idx] or "").strip()

        def is_ref(l):
            # Referenca tipa: 1e65:00eb0000:0c9e:0003:22:0:0
            return ":" in l and len(l.split(":")) >= 7 and all(part.strip() for part in l.split(":")[:7])

        def is_pline(l):
            ll = l.lower()
            return any(t in ll for t in ["p:", "c:", "f:", "C:"])

        # 1. Ako je selektovana REF linija (npr. 3c3c:00eb0000:0c90:0003:25:0:0)
        if is_ref(line):
            ref_line = line
            name = ""
            pline = ""
            # Uzmi sledeće dve linije ako postoje (name i pline)
            if selected_idx + 1 < len(items):
                name = items[selected_idx + 1].strip()
            if selected_idx + 2 < len(items):
                pline = items[selected_idx + 2].strip()
            print("[Extract] REF case → ref:", ref_line, "name:", name, "pline:", pline)
            return {
                "ref": ref_line,
                "sid_line": ref_line,  # OVO JE KLJUČNO za editor!
                "name": name,
                "pline": pline
            }

        # 2. Ako je selektovan NAME red (prethodna linija je REF)
        if selected_idx - 1 >= 0 and is_ref(items[selected_idx - 1].strip()):
            ref_line = items[selected_idx - 1].strip()
            name = line
            pline = ""
            if selected_idx + 1 < len(items):
                pline = items[selected_idx + 1].strip()
            print("[Extract] NAME case → ref:", ref_line, "name:", name, "pline:", pline)
            return {
                "ref": ref_line,
                "sid_line": ref_line,
                "name": name,
                "pline": pline
            }

        # 3. Ako je selektovan PLINE red (dve linije iznad je REF)
        if is_pline(line) and selected_idx - 2 >= 0 and is_ref(items[selected_idx - 2].strip()):
            ref_line = items[selected_idx - 2].strip()
            name = ""
            if selected_idx - 1 >= 0:
                name = items[selected_idx - 1].strip()
            pline = line
            print("[Extract] PLINE case → ref:", ref_line, "name:", name, "pline:", pline)
            return {
                "ref": ref_line,
                "sid_line": ref_line,
                "name": name,
                "pline": pline
            }

        print("[Extract] No valid service found around index", selected_idx, "line:", line)
        return None

    def addFakeT2MI(self):
        # Uzmi default iz aktivnog tunera
        default_freq = 11778
        default_sr = 15155
        service = self.session.nav.getCurrentService()
        if service:
            feInfo = service.frontendInfo()
            if feInfo:
                feData = feInfo.getAll(True)
                if feData:
                    default_freq = feData.get("frequency", 11778000) // 1000
                    default_sr = feData.get("symbol_rate", 15155000) // 1000
        self.session.open(AddFakeT2MIScreen, self.orbital_pos, default_freq, default_sr)

    def openLamedbEditor(self):
        # Uzmi podatke od selektovanog servisa (kao i ranije)
        current = self["list"].getCurrent()
        if not current:
            self.session.open(MessageBox, "Ništa nije selektovano!", MessageBox.TYPE_INFO)
            return

        current_str = current if isinstance(current, str) else current[0]

        # Ako je TP linija – preskoči edit (samo prikaz)
        if current_str.startswith("TP:"):
            self.session.open(MessageBox, "Transponder je samo za prikaz (edit preko servisa)", MessageBox.TYPE_INFO, timeout=4)
            return

        # Uzmi podatke selektovanog servisa
        entry = self._extract_service_entry_from_list(self["list"].getSelectionIndex())
        if not entry:
            self.session.open(MessageBox, "Nema podataka o servisu!", MessageBox.TYPE_ERROR)
            return

        # Dodaj TP podatke od AKTIVNOG tunera (ne od TP liste)
        tp_data = None
        service = self.session.nav.getCurrentService()
        if service:
            feInfo = service.frontendInfo()
            if feInfo:
                feData = feInfo.getAll(True)
                if feData and feData.get("tuner_type") == "DVB-S":
                    freq_khz = feData.get("frequency", 0) // 1000
                    sr_khz   = feData.get("symbol_rate", 0) // 1000
                    pol      = feData.get("polarization", 0)   # 0=H, 1=V
                    fec      = feData.get("fec_inner", 0)
                    orb      = feData.get("orbital_position", self.orbital_pos)
                    inv      = feData.get("inversion", 2)
                    sys      = feData.get("system", 1)         # 0=DVB-S, 1=DVB-S2
                    mod      = feData.get("modulation", 1)     # 1=QPSK, 2=8PSK...
                    ro       = feData.get("rolloff", 0)
                    pilot    = feData.get("pilot", 2)

                    tp_params = f"{freq_khz}:{sr_khz}:{pol}:{fec}:{orb}:{inv}:0:{sys}:{mod}:{ro}:{pilot}"
                    tp_data = {
                        'tp_key': f"{hex(freq_khz)[2:]}:{hex(feData.get('transponder_id', 0))[2:]}:ffff",  # približno
                        'full_params': tp_params,
                        'original_prefix': 's'  # standardno za satelit
                    }
                    print("[openLamedbEditor] Dodat TP od aktivnog tunera:", tp_params)

        # Otvori postojeći editor sa service + tp podacima
        self.session.open(LamedbEditorScreen, entry, tp_data, self)

    def getCurrentChannelName(self):
        service = self.session.nav.getCurrentService()
        if service:
            info = service.info()
            if info:
                name = info.getName()
                if name:
                    return name.strip()
        return ""

    def _moveSelectionToIndex(self, idx):
        # MenuList u većini image-ova ima moveToIndex()
        try:
            if hasattr(self["list"], "moveToIndex"):
                self["list"].moveToIndex(idx)
                return
        except:
            pass

        # Fallback (različite implementacije)
        try:
            if hasattr(self["list"], "instance") and self["list"].instance:
                self["list"].instance.moveSelectionTo(idx)
        except:
            pass
    def getCurrentServiceRefString(self):
        # Enigma2 ref string, npr: "1:0:19:307:C94:3:EB0000:0:0:0:"
        try:
            sref = self.session.nav.getCurrentlyPlayingServiceReference()
            if sref:
                return (sref.toString() or "").strip()
        except:
            pass
        return ""

    def enigmaRefToDataBrowserRef(self, enigma_ref):
        """
        Pretvori Enigma2 ref u format koji DataBrowser prikazuje:
        sid:namespace:tsid:onid:stype:flags:0   (sve u hex, sa padovanjem gde treba)
        """
        if not enigma_ref:
            return ""

        parts = [p for p in enigma_ref.strip().split(":") if p != ""]
        # očekujemo bar: 1:flags:stype:sid:tsid:onid:namespace:...
        if len(parts) < 7:
            return ""

        try:
            flags = int(parts[1], 16)
            stype = int(parts[2], 16)
            sid = int(parts[3], 16)
            tsid = int(parts[4], 16)
            onid = int(parts[5], 16)
            namespace = int(parts[6], 16)
        except:
            return ""

        # DataBrowser format iz lamedb-a: sid(4) : ns(8) : tsid(4) : onid(4) : stype(2) : flags(no-pad) : 0
        return f"{sid:04x}:{namespace:08x}:{tsid:04x}:{onid:04x}:{stype:02x}:{flags:x}:0"

    def _moveSelectionToIndex(self, idx):
        try:
            if hasattr(self["list"], "moveToIndex"):
                self["list"].moveToIndex(idx)
                return
        except:
            pass
        try:
            if hasattr(self["list"], "instance") and self["list"].instance:
                self["list"].instance.moveSelectionTo(idx)
        except:
            pass

    def reload(self):
        try:
            sat_txt = self.parent.formatOrbitalPos(self.orbital_pos) if hasattr(self.parent,
                                                                                "formatOrbitalPos") else str(
                self.orbital_pos)
            # === NOVA LINIJA: Učitavamo i transpondere ===
            tps = self._load_transponders_for_orbital(self.orbital_pos)
            print(f"[DataBrowserScreen] Found {len(tps)} transponders")

            items = self._load_data_services_for_orbital(self.orbital_pos)
            print(f"[DataBrowserScreen] Found {len(items)} items (services)")

            if not items and not tps:
                self["status"].setText(f"No services or transponders found for {sat_txt}")
                self["list"].setList([f"No data found for {sat_txt}"])
                return

            self["status"].setText(f"Services + TPs on {sat_txt}: {len(items)} serv. + {len(tps)} TP")

            # Formatiraj svaki red za prikaz
            formatted_items = []

            # === NOVI DEO: Prvo prikazujemo TRANSPO NDERE ===
            if tps:
                formatted_items.append("")
                formatted_items.append(f"{'─' * 60} TRANSPONDERS ({len(tps)}) {'─' * 60}")
                for tp in tps:
                    formatted_items.append(f"TP: {tp['tp_key']}")
                    formatted_items.append(f"   {tp['info']}")
                    formatted_items.append(f"   Params: {tp['full_params']}")
                    formatted_items.append("")  # razmak između TP-ova

            # === POSTOJEĆI DEO: Servisi (grupisani po TP-ovima) ===
            tp_services = {}
            for service in items:
                tp_key = service.get('tp_key', 'Unknown')
                if tp_key not in tp_services:
                    tp_services[tp_key] = []
                tp_services[tp_key].append(service)

            for tp_key, services in tp_services.items():
                # Prikaži liniju transpondera (kao ranije)
                if tp_key != 'Unknown':
                    tp_info = services[0].get('tp_info', 'Unknown Transponder')
                    if tp_info:
                        formatted_items.append("")
                        formatted_items.append(f"{'─' * 100}")
                        formatted_items.append(f"TP: {tp_key} → {tp_info}")
                        formatted_items.append(f"{'─' * 100}")

                # Prikaži servise za ovaj TP (kao ranije)
                for service in services:
                    name = service.get('name', 'Unknown')
                    ref = service.get('ref', '')
                    pids = service.get('pids', '')
                    provider = service.get('provider', '')

                    formatted_items.append(f"{ref}")
                    formatted_items.append(f"{name}")
                    if provider and provider != "?" and provider != "Unknown":
                        formatted_items.append(f"{provider}")
                    if pids:
                        for pid_line in pids.split(' '):
                            if pid_line:
                                formatted_items.append(f"{pid_line}")
                    formatted_items.append("")

            if not formatted_items:
                formatted_items = ["No data to display"]

            self["list"].setList(formatted_items)
            self.formatted_items = formatted_items

            # ... (ostatak metode za pomeranje selekcije - ostaje isti)

            moved = False
            # 1) Precizno: po service ref-u
            enigma_ref = self.getCurrentServiceRefString()
            target_ref = self.enigmaRefToDataBrowserRef(enigma_ref).lower().strip()
            if target_ref:
                for i, line in enumerate(formatted_items):
                    if line and line.lower().strip() == target_ref:
                        self._moveSelectionToIndex(i + 1 if (i + 1) < len(formatted_items) else i)
                        moved = True
                        break

            # 2) Fallback: po imenu
            if not moved:
                current_name = self.getCurrentChannelName()
                if current_name:
                    for i, line in enumerate(formatted_items):
                        if line and line.strip() == current_name:
                            self._moveSelectionToIndex(i)
                            break

        except Exception as e:
            print(f"[DataBrowserScreen] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            self["status"].setText("ERROR: %s" % str(e))
            self["list"].setList([f"ERROR: {str(e)}"])

    def namespace_to_orbital(self, ns_hex):
        try:
            ns_clean = ns_hex.lstrip('0').upper() if ns_hex else '0'
            ns_int = int(ns_clean, 16)
            orb_int = (ns_int >> 16) & 0xFFFF
            if orb_int > 1800:
                orb_int = 3600 - orb_int
            return orb_int
        except:
            return -1

    def _load_data_services_for_orbital(self, orbital_pos):
        """Učitaj servise iz lamedb za dati orbital"""
        lamedb = "/etc/enigma2/lamedb"
        if not os.path.exists(lamedb):
            print("[DataBrowserScreen] lamedb not found")
            return []

        try:
            with open(lamedb, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.rstrip() for ln in f]
            print(f"[DataBrowserScreen] Read {len(lines)} lines from lamedb")
        except Exception as e:
            print(f"[DataBrowserScreen] Error reading lamedb: {e}")
            return []

        # Prvo učitaj transpondere
        tp_map = {}
        i = 0
        transponder_count = 0
        while i < len(lines):
            line = lines[i].strip()
            if line == "transponders":
                i += 1
                while i < len(lines) and lines[i].strip() != "/":
                    key = lines[i].strip().lower()
                    i += 1
                    if i < len(lines) and lines[i].startswith("t "):
                        p = lines[i][2:].split(":")
                        if len(p) >= 5:
                            # Format: t frequency:sr:polarization:fec:system:modulation:...
                            freq = int(p[0]) // 1000 if p[0].isdigit() else 0
                            sr = int(p[1]) // 1000 if p[1].isdigit() else 0
                            pol = {"0": "H", "1": "V", "2": "L", "3": "R"}.get(p[2], "?")

                            # Dohvati FEC
                            fec_val = int(p[3]) if len(p) > 3 and p[3].isdigit() else 0
                            fec = self.parent.getFec(fec_val) if hasattr(self.parent, "getFec") else str(fec_val)

                            # Dohvati system i modulaciju
                            system = "DVB-S"
                            modulation = ""
                            if len(p) > 5:
                                system = "DVB-S2" if p[5] == "1" else "DVB-S"
                                if len(p) > 6 and p[6].isdigit():
                                    mod_val = int(p[6])
                                    modulation = self.parent.getModulation(mod_val) if hasattr(self.parent,
                                                                                               "getModulation") else str(
                                        mod_val)

                            tp_info = f"{freq} {pol} {sr} {fec} {modulation} {system}".strip()
                            orb_str = p[4] if len(p) > 4 else "-1"
                            orb = int(orb_str) if orb_str.isdigit() else -1
                            tp_map[key] = {
                                'orbital': orb,
                                'info': tp_info
                            }
                            transponder_count += 1
                    i += 1
                continue
            i += 1

        print(f"[DataBrowserScreen] Found {transponder_count} transponders")

        # Zatim učitaj servise
        services = []
        i = 0
        service_count = 0
        orbital_match_count = 0

        while i < len(lines):
            line = lines[i].strip()
            if line == "services":
                i += 1
                while i < len(lines) and lines[i].strip() != "end":
                    header = lines[i].strip()
                    if not header or ":" not in header:
                        i += 1
                        continue

                    fields = header.split(":")
                    if len(fields) < 6:
                        i += 1
                        continue

                    sid_h, ns_h, tsid_h, onid_h, stype_h, flags_h = fields[:6]
                    try:
                        sid = int(sid_h, 16)
                        stype = int(stype_h, 16)
                        flags = int(flags_h, 16) if flags_h else 0
                    except:
                        i += 1
                        continue

                    name = lines[i + 1].strip() if i + 1 < len(lines) else "?"
                    provider = lines[i + 2].strip() if i + 2 < len(lines) else ""

                    # Prikupi cached informacije (PID-ovi)
                    cached = []
                    j = i + 3
                    while j < len(lines):
                        if j >= len(lines):
                            break
                        cl = lines[j].strip()
                        # Ako naiđemo na novi header (sadrži : i dovoljno polja), prekidamo
                        if cl and ":" in cl and len(cl.split(":")) >= 6:
                            break
                        if cl.startswith(("p:", "c:", "C:", "f:")):
                            cached.append(cl)
                        j += 1
                    i = j

                    service_count += 1

                    # Dohvati orbital iz transpondera
                    ns_clean = ns_h.lstrip('0').lower() or '0'
                    tp_key = f"{ns_clean}:{tsid_h}:{onid_h}"
                    tp_data = tp_map.get(tp_key, {'orbital': -1, 'info': ''})

                    if tp_data['orbital'] == -1:
                        tp_data['orbital'] = self.namespace_to_orbital(ns_h)

                    # Filter za aktivni orbital
                    if tp_data['orbital'] != int(orbital_pos):
                        continue

                    orbital_match_count += 1

                    # Formiraj referencu
                    ref = f"{sid:04x}:{ns_h}:{tsid_h}:{onid_h}:{stype_h}:{flags_h}:0"

                    # Formiraj PID string - spojene sve cached linije
                    pids_str = " ".join(cached) if cached else ""

                    services.append({
                        'name': name,
                        'ref': ref,
                        'provider': provider if provider != "?" else "",
                        'pids': pids_str,
                        'tp_key': tp_key,
                        'tp_info': tp_data['info'],
                        'stype': stype,
                        'flags': flags
                    })

                break
            i += 1

        print(f"[DataBrowserScreen] Total services: {service_count}")
        print(f"[DataBrowserScreen] Orbital match: {orbital_match_count}")
        print(f"[DataBrowserScreen] After filter: {len(services)}")

        # Sortiraj po transponder info pa po imenu
        services.sort(key=lambda x: (x['tp_info'], x['name']))

        return services

    # === NOVA METODA: Učitavanje transpondera za aktivni satelit ===
    def _load_transponders_for_orbital(self, orbital_pos):
        """Učitava samo SATELITSKE transpondere iz lamedb-a za dati orbital"""
        lamedb = "/etc/enigma2/lamedb"
        if not os.path.exists(lamedb):
            print("[DataBrowserScreen] lamedb not found")
            return []

        try:
            with open(lamedb, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.rstrip() for ln in f]
        except Exception as e:
            print(f"[DataBrowserScreen] Error reading lamedb: {e}")
            return []

        tp_list = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line and ':' in line and len(line.split(':')) == 3:
                key = line.strip().upper()  # npr. 01860000:03EA:FFFF
                i += 1
                if i < len(lines):
                    tp_line = lines[i].strip()
                    if tp_line.startswith(('s ', 't ')):  # podržavamo i s i t, ali filtriramo kasnije
                        params_str = tp_line[2:]
                        p = params_str.split(':')

                        if len(p) < 5:
                            i += 1
                            continue

                        # Orbital position je NA INDEXU 4 !!!
                        try:
                            orb = int(p[4])
                        except (ValueError, IndexError):
                            i += 1
                            continue

                        # Preskoči ako nije traženi orbital
                        if orb != int(orbital_pos):
                            i += 1
                            continue

                        # Ovo je validan satelitski TP za traženi satelit
                        freq = int(p[0]) // 1000 if p[0].isdigit() else 0
                        sr   = int(p[1]) // 1000 if len(p) > 1 and p[1].isdigit() else 0
                        pol  = {"0":"H", "1":"V", "2":"L", "3":"R"}.get(p[2] if len(p)>2 else "0", "?")
                        fec_val = int(p[3]) if len(p)>3 and p[3].isdigit() else 0
                        fec  = self.parent.getFec(fec_val) if hasattr(self.parent, 'getFec') else str(fec_val)

                        # Sistem / modulacija
                        sys_str = "DVB-S"
                        if len(p) > 7 and p[7] == "1":
                            sys_str = "DVB-S2"
                        elif "8PSK" in params_str or "16APSK" in params_str or "32APSK" in params_str:
                            sys_str = "DVB-S2"

                        tp_info = f"{freq:5} {pol} {sr:5}  {fec}  {sys_str}"

                        tp_list.append({
                            'tp_key': key,
                            'info': tp_info.strip(),
                            'full_params': params_str,
                            'orbital': orb,
                            'system': sys_str
                        })

                        print(f"[TP ADD] {key} → {tp_info}  (orbital={orb})")

            i += 1

        # Sort po frekvenciji (po namespace delu ključa)
        tp_list.sort(key=lambda x: int(x['tp_key'].split(':')[0], 16) if ':' in x['tp_key'] else 0)

        sat_name = self.parent.formatOrbitalPos(orbital_pos) if hasattr(self.parent, 'formatOrbitalPos') else f"{orbital_pos/10:.1f}°"
        print(f"[DataBrowserScreen] Pronađeno {len(tp_list)} SATELITSKIH transpondera za {sat_name}")
        return tp_list
    
class LamedbEditorScreen(Screen):
    skin = """
    <screen name="LamedbEditorScreen" position="center,center" size="1800,900" title="..:: Lamedb Editor ::..">
        <eLabel position="0,0" size="1800,900" backgroundColor="#0D1B36" zPosition="-1" />

        <widget name="list" position="40,60" size="1720,720" scrollbarMode="showOnDemand"
                foregroundColor="#ffffff" backgroundColor="#1a1a1a" font="Console;24" />

        <widget name="status" position="40,790" size="1720,40" font="Regular;22"
                foregroundColor="#BBBBBB" halign="left" valign="center" transparent="1" />

        <widget name="key_red" position="120,840" size="320,40" backgroundColor="red"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_green" position="520,840" size="320,40" backgroundColor="green"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_yellow" position="920,840" size="320,40" backgroundColor="yellow"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_blue" position="1320,840" size="320,40" backgroundColor="blue"
                font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
    </screen>
    """

    LAMEDB_PATH = "/etc/enigma2/lamedb"

    def __init__(self, session, entry, tp_data=None, parent=None):
        """
        entry = {"ref": "...", "name": "...", "pline": "..."}
        tp_data = {"tp_key": "...", "full_params": "..."}  # opciono, stiže iz DataBrowserScreen
        parent = DataBrowserScreen (opciono, za refresh posle save)
        """
        Screen.__init__(self, session)
        self.parent = parent
        self.original_ref = (entry.get("ref") or "").strip()
        self.ref = self.original_ref
        self.name = (entry.get("name") or "").strip()
        self.pline = (entry.get("pline") or "").strip()
        self.sid_line = (entry.get("sid_line") or "").strip()

        # TP podaci (opciono)
        self.tp_data = tp_data or {}
        self.edited_tp_params = self.tp_data.get('full_params', '').split(':') if self.tp_data else []
        self.original_tp_params = self.tp_data.get('full_params', '')

        print("[Editor] SID line from entry:", repr(self.sid_line))
        self._parse_sid_line(self.sid_line)
        print("[Editor] Parsed SID values:", self.sid_val, self.ns_val, self.tsid_val, self.onid_val, self.stype_val,
              self.sflags_val, self.dummy_val)

        # SID mode (0=full, 1=custom)
        self.sid_mode = 0
        self._parse_sid_line(self.sid_line)

        self.mode = "default"  # default|custom

        self.flags_options = [f"f:{i}" for i in range(0, 33)]

        # Custom delovi (popunjava se iz pline)
        self.custom_provider = "p:"
        self.custom_data_pid = "c:"
        self.custom_flags = "f:0"
        self.custom_other_tokens = []  # sve ostalo što ne menjamo

        # Encryption/CAID
        self.custom_caid = ""  # "" znači None
        self.caid_options = ["", "C:2600", "C:0500", "C:0604", "C:0B00", "C:0D96", "C:181D"]

        self._parse_pline_to_custom(self.pline)

        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Button("Cancel")
        self["key_green"] = Button("Save")
        self["key_yellow"] = Button("Default/Custom")
        self["key_blue"] = Button("Reload DB")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.keyCancel,
                "ok": self.keyOK,
                "red": self.keyCancel,
                "green": self.keySave,
                "yellow": self.toggleMode,
                "blue": self.reloadE2DB,
                "up": self["list"].up,
                "down": self["list"].down,
                "left": self.keyLeft,
                "right": self.keyRight,
            },
            -2
        )

        self.onLayoutFinish.append(self.refreshList)

    def _sidLineEdited(self, text):
        if text:
            self.sid_line = text.strip()
            self._parse_sid_line(self.sid_line)
            self.refreshList()

    def _editSidField(self, attr, value):
        self.session.openWithCallback(
            lambda txt: self._sidFieldEdited(attr, txt),
            VirtualKeyBoard,
            title="Edit %s" % attr,
            text=value
        )

    def _sidFieldEdited(self, attr, text):
        if text:
            setattr(self, attr, text.strip())
            self.sid_line = self._build_sid_line()
            self.refreshList()


    # ---------------- UI list ----------------
    def refreshList(self):
        items = []

        # Ref (uvek prva)
        items.append("Edit SID/NS/TID/NID ------ %s" % self.ref)

        # SID sekcija
        if self.mode == "custom" and self.sid_mode == 1:
            items.append("Edit SID Line ------ Custom")
            items.append(" SID ------ %s" % (self.sid_val or "0"))
            items.append(" Namespace ------ %s" % (self.ns_val or "0"))
            items.append(" TSID ------ %s" % (self.tsid_val or "0"))
            items.append(" ONID ------ %s" % (self.onid_val or "0"))
            items.append(" Service type ------ %s" % (self.stype_val or "0"))
            items.append(" Flags ------ %s" % (self.sflags_val or "0"))
            items.append(" Dummy ------ %s" % (self.dummy_val or "0"))
        else:
            items.append("Edit SID Line ------ %s" % (self.sid_line or ""))

        # Name
        items.append("Edit Name ------ %s" % (self.name or ""))

        # Prov/PID sekcija
        if self.mode == "custom":
            items.append("Edit Prov/PID ------ Custom")
            items.append(" Edit Provider ------ %s" % (self.custom_provider or "p:"))
            items.append(" Edit Data pid ------ %s" % (self.custom_data_pid or "c:"))
            items.append(" Edit Flags ------ %s" % (self.custom_flags or "f:0"))
            items.append(" Edit Encryption ------ %s" % (self.custom_caid or "None"))
            items.append(
                " Other tokens ------ %s" % (",".join(self.custom_other_tokens) if self.custom_other_tokens else "-"))
            items.append(" Add new token ------ (press OK to add)")  # ← NOVA LINIJA
        else:
            items.append("Edit Prov/PID line ------ %s" % (self.pline or ""))
        # --- Transponder sekcija ---
        items.append("")
        items.append("--- Transponder (od aktivnog kanala) ---")
        if self.edited_tp_params:
            tp_fields = [
                ("Frequency", 0),
                ("Symbol Rate", 1),
                ("Polarization", 2),
                ("FEC", 3),
                ("Orbital", 4),
                ("Inversion", 5),
                ("System", 7),
                ("Modulation", 8),
                ("Roll-off", 9),
                ("Pilot", 10),
            ]
            for name, idx in tp_fields:
                val = self.edited_tp_params[idx] if len(self.edited_tp_params) > idx else "?"
                items.append(f"  Edit {name} ------ {val}")
        else:
            items.append("  Nema TP podataka (nije satelitski tuner)")

        # Mode info
        items.append("")
        items.append("Mode: %s (Yellow = toggle)" % ("DEFAULT" if self.mode == "default" else "CUSTOM"))

        # Original ref
        items.append("")
        items.append("Original ref: %s" % self.original_ref)

        # Postavi listu
        self["list"].setList(items)

        self["status"].setText("OK=Edit | Green=Save | Yellow=Mode | Blue=Reload DB")

    def _getSelectedLine(self):
        try:
            sel = self["list"].getCurrent()
            return (sel or "").strip()
        except:
            return ""

    # ---------------- Key handling ----------------

    def keyCancel(self):
        self.close(False)

    def toggleMode(self):
        if self.mode == "default":
            self.mode = "custom"
            self.sid_mode = 1  # automatski uključi razlaganje SID-a u custom modu
        else:
            self.mode = "default"
            self.sid_mode = 0  # vrati na punu liniju
        self.refreshList()

    def keyLeft(self):
        if self.mode != "custom":
            return
        line = self._getSelectedLine()
        if line.startswith("Edit Flags") or line.startswith("Edit Flags".lower()) or "Edit Flags" in line:
            self._cycle_flags(-1)
        if "Edit Encryption" in line:
            self._cycle_caid(-1)
        current = self["list"].getCurrent()

        if current and current[0] == "Edit SID Line":
            self.toggleSidMode()
            return

        SERVICE_TYPES = ["1", "2", "19", "22", "25"]

        if current and current[0] == "Service Type":
            idx = SERVICE_TYPES.index(self.stype_val) if self.stype_val in SERVICE_TYPES else 0
            if direction == "left":
                idx = (idx - 1) % len(SERVICE_TYPES)
            else:
                idx = (idx + 1) % len(SERVICE_TYPES)

            self.stype_val = SERVICE_TYPES[idx]
            self.sid_line = self._build_sid_line()
            self.refreshList()
            return

    def keyRight(self):
        if self.mode != "custom":
            return
        line = self._getSelectedLine()
        if line.startswith("Edit Flags") or line.startswith("Edit Flags".lower()) or "Edit Flags" in line:
            self._cycle_flags(1)
        if "Edit Encryption" in line:
            self._cycle_caid(1)
        current = self["list"].getCurrent()

        if current and current[0] == "Edit SID Line":
            self.toggleSidMode()
            return

        SERVICE_TYPES = ["1", "2", "19", "22", "25"]

        if current and current[0] == "Service Type":
            idx = SERVICE_TYPES.index(self.stype_val) if self.stype_val in SERVICE_TYPES else 0
            if direction == "left":
                idx = (idx - 1) % len(SERVICE_TYPES)
            else:
                idx = (idx + 1) % len(SERVICE_TYPES)

            self.stype_val = SERVICE_TYPES[idx]
            self.sid_line = self._build_sid_line()
            self.refreshList()
            return

    def keyOK(self):
        line = self._getSelectedLine()
        if not line:
            return

        from Screens.VirtualKeyBoard import VirtualKeyBoard

        # 1. Edit REF (SID/NS/TID/NID) - uvek
        if line.startswith("Edit SID/NS/TID/NID"):
            self.session.openWithCallback(
                self._vk_ref_done,
                VirtualKeyBoard,
                title="Edit service ref (SID:NS:TSID:ONID:STYPE:FLAGS:0)",
                text=self.ref
            )
            return

        # 2. Edit Name - uvek
        if line.startswith("Edit Name"):
            self.session.openWithCallback(
                self._vk_name_done,
                VirtualKeyBoard,
                title="Edit service name",
                text=self.name
            )
            return

        # 3. Default mode - edit celog Prov/PID line
        if self.mode == "default" and line.startswith("Edit Prov/PID line"):
            self.session.openWithCallback(
                self._vk_pline_done,
                VirtualKeyBoard,
                title="Edit provider/PID line (p:/c:/f: ...)",
                text=self.pline
            )
            return

        # 4. Custom mode - Prov/PID polja
        if self.mode == "custom":
            if "Edit Provider" in line:
                self.session.openWithCallback(
                    self._vk_provider_done,
                    VirtualKeyBoard,
                    title="Edit provider token (example: p:SES)",
                    text=self.custom_provider
                )
                return

            if "Edit Data pid" in line:
                self.session.openWithCallback(
                    self._vk_data_pid_done,
                    VirtualKeyBoard,
                    title="Edit data pid token (example: c:151001)",
                    text=self.custom_data_pid
                )
                return

            # Flags i Encryption - ciklus (možeš promeniti na VK ako želiš)
            if "Edit Flags" in line:
                self._cycle_flags(1)
                return

            if "Edit Encryption" in line:
                self._cycle_caid(1)
                return

        if self.mode == "custom" and "Add new token" in line:
            self.session.openWithCallback(
                self._vk_add_token_done,
                VirtualKeyBoard,
                title="Add new token (example: c:190021, f:4, C:2600, etc.)",
                text=""
            )
            return
        # Transponder edit polja (dodato za edit TP od aktivnog kanala)
        # Transponder edit polja - koristi VirtualKeyBoard (kao za service polja)
        if "Edit Frequency" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(0, val),
                VirtualKeyBoard,
                title="Edit Frequency (kHz)",
                text=self.edited_tp_params[0] if len(self.edited_tp_params) > 0 else "0"
            )
            return
        elif "Edit Symbol Rate" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(1, val),
                VirtualKeyBoard,
                title="Edit Symbol Rate (kSym/s)",
                text=self.edited_tp_params[1] if len(self.edited_tp_params) > 1 else "0"
            )
            return
        elif "Edit Polarization" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(2, val),
                VirtualKeyBoard,
                title="Edit Polarization (0=H,1=V,2=L,3=R)",
                text=self.edited_tp_params[2] if len(self.edited_tp_params) > 2 else "0"
            )
            return
        elif "Edit FEC" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(3, val),
                VirtualKeyBoard,
                title="Edit FEC (0=auto,3=3/4,4=5/6,...)",
                text=self.edited_tp_params[3] if len(self.edited_tp_params) > 3 else "0"
            )
            return
        elif "Edit Orbital" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(4, val),
                VirtualKeyBoard,
                title="Edit Orbital position",
                text=self.edited_tp_params[4] if len(self.edited_tp_params) > 4 else "0"
            )
            return
        elif "Edit Inversion" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(5, val),
                VirtualKeyBoard,
                title="Edit Inversion (0=off,1=on,2=auto)",
                text=self.edited_tp_params[5] if len(self.edited_tp_params) > 5 else "0"
            )
            return
        elif "Edit System" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(7, val),
                VirtualKeyBoard,
                title="Edit System (0=DVB-S,1=DVB-S2)",
                text=self.edited_tp_params[7] if len(self.edited_tp_params) > 7 else "0"
            )
            return
        elif "Edit Modulation" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(8, val),
                VirtualKeyBoard,
                title="Edit Modulation (1=QPSK,2=8PSK,...)",
                text=self.edited_tp_params[8] if len(self.edited_tp_params) > 8 else "0"
            )
            return
        elif "Edit Roll-off" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(9, val),
                VirtualKeyBoard,
                title="Edit Roll-off (0=0.35,1=0.25,...)",
                text=self.edited_tp_params[9] if len(self.edited_tp_params) > 9 else "0"
            )
            return
        elif "Edit Pilot" in line:
            self.session.openWithCallback(
                lambda val: self._tp_field_edited(10, val),
                VirtualKeyBoard,
                title="Edit Pilot (0=off,1=on,2=auto)",
                text=self.edited_tp_params[10] if len(self.edited_tp_params) > 10 else "0"
            )
            return

        # SID custom fields
        if self.sid_mode == 1:
            if line.startswith("SID "):
                self.session.openWithCallback(
                    self._vk_sid_val_done,
                    VirtualKeyBoard,
                    title="Edit SID value",
                    text=self.sid_val
                )
                return
            elif line.startswith("Namespace "):
                self.session.openWithCallback(
                    self._vk_ns_val_done,
                    VirtualKeyBoard,
                    title="Edit Namespace value",
                    text=self.ns_val
                )
                return
            elif line.startswith("TSID "):
                self.session.openWithCallback(
                    self._vk_tsid_val_done,
                    VirtualKeyBoard,
                    title="Edit TSID value",
                    text=self.tsid_val
                )
                return
            elif line.startswith("ONID "):
                self.session.openWithCallback(
                    self._vk_onid_val_done,
                    VirtualKeyBoard,
                    title="Edit ONID value",
                    text=self.onid_val
                )
                return
            elif line.startswith("Service type "):
                self.session.openWithCallback(
                    self._vk_stype_val_done,
                    VirtualKeyBoard,
                    title="Edit Service type value",
                    text=self.stype_val
                )
                return
            elif line.startswith("Flags "):
                self.session.openWithCallback(
                    self._vk_sflags_val_done,
                    VirtualKeyBoard,
                    title="Edit Flags value",
                    text=self.sflags_val
                )
                return
            elif line.startswith("Dummy "):
                self.session.openWithCallback(
                    self._vk_dummy_val_done,
                    VirtualKeyBoard,
                    title="Edit Dummy value",
                    text=self.dummy_val
                )
                return
            
        if "Edit SID Line" in line:
            if self.sid_mode == 0:
                # Full edit
                self.session.openWithCallback(
                    self._sidLineEdited,
                    VirtualKeyBoard,
                    title="Edit SID Line (SID:NS:TSID:ONID:STYPE:FLAGS:0)",
                    text=self.sid_line
                )
            else:
                # Custom SID polja - provera po početku linije (bez zavisnosti od crtica)
                if line.startswith("SID "):
                    self._editSidField("sid_val", self.sid_val)
                elif line.startswith("Namespace "):
                    self._editSidField("ns_val", self.ns_val)
                elif line.startswith("TSID "):
                    self._editSidField("tsid_val", self.tsid_val)
                elif line.startswith("ONID "):
                    self._editSidField("onid_val", self.onid_val)
                elif line.startswith("Service type "):
                    self._editSidField("stype_val", self.stype_val)
                elif line.startswith("Flags "):
                    self._editSidField("sflags_val", self.sflags_val)
                elif line.startswith("Dummy "):
                    self._editSidField("dummy_val", self.dummy_val)
            return

        # Debug ako ništa ne matchuje
        print("[Editor] No action for line:", repr(line))

    # ---------------- VK callbacks za SID custom polja ----------------
    def _vk_sid_val_done(self, result):
        if result is not None:
            self.sid_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_ns_val_done(self, result):
        if result is not None:
            self.ns_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_tsid_val_done(self, result):
        if result is not None:
            self.tsid_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_onid_val_done(self, result):
        if result is not None:
            self.onid_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_stype_val_done(self, result):
        if result is not None:
            self.stype_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_sflags_val_done(self, result):
        if result is not None:
            self.sflags_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_dummy_val_done(self, result):
        if result is not None:
            self.dummy_val = result.strip()
            self.sid_line = self._build_sid_line()
            self.refreshList()

    def _vk_ref_done(self, result):
        if result:
            self.ref = result.strip()
            self.refreshList()

    def _vk_name_done(self, result):
        if result:
            self.name = result.strip()
            self.refreshList()

    def _vk_pline_done(self, result):
        if result is not None:
            self.pline = result.strip()
            self._parse_pline_to_custom(self.pline)
            self.refreshList()

    def _vk_provider_done(self, result):
        if result:
            self.custom_provider = result.strip()
            self.refreshList()

    def _vk_data_pid_done(self, result):
        if result:
            self.custom_data_pid = result.strip()
            self.refreshList()

    def _vk_add_token_done(self, result):
        if result is not None:
            token = result.strip()
            if not token:
                return

            # Dodaj u odgovarajuću listu
            if token.startswith("p:"):
                self.custom_provider = token
            elif token.startswith("c:"):
                if token not in self.custom_data_pid:  # izbegni duplikate
                    self.custom_data_pid += "," + token if self.custom_data_pid != "c:" else token
            elif token.startswith("f:"):
                self.custom_flags = token
            elif token.startswith("C:"):
                self.custom_caid = token
            else:
                # sve ostalo ide u other tokens
                if token not in self.custom_other_tokens:
                    self.custom_other_tokens.append(token)

            self.refreshList()

    # ---------------- Custom parsing/building ----------------
    def _parse_pline_to_custom(self, pline):
        if not pline:
            return

        tokens = [t.strip() for t in pline.split(",") if t.strip()]

        p_tok = None
        c_toks = []
        f_tok = None
        caid = ""
        other = []

        for t in tokens:

            # PROVIDER
            if t.startswith("p:") and p_tok is None:
                p_tok = t
                continue

            # DATA PID (lowercase c:)
            if t.startswith("c:"):
                c_toks.append(t)
                continue

            # FLAGS
            if t.startswith("f:") and f_tok is None:
                f_tok = t
                continue

            # ENCRYPTION / CAID (uppercase C:)
            if t.startswith("C:") and caid == "":
                caid = t
                continue

            # sve ostalo
            other.append(t)

        self.custom_provider = p_tok if p_tok else "p:"
        self.custom_flags = f_tok if f_tok else "f:0"
        self.custom_caid = caid  # "" znači None

        # heuristika za data pid (kao ranije)
        preferred = None
        for t in c_toks:
            if t.lower().startswith("c:15") or t.lower().startswith("c:18"):
                preferred = t
        self.custom_data_pid = preferred if preferred else (c_toks[-1] if c_toks else "c:")

        self.custom_other_tokens = other

    def _parse_sid_line(self, sid_line):
        print("[Parse] Input SID line:", repr(sid_line))
        parts = sid_line.split(":")
        print("[Parse] Parts:", parts)
        while len(parts) < 7:
            parts.append("0")
        self.sid_val = parts[0]
        self.ns_val = parts[1]
        self.tsid_val = parts[2]
        self.onid_val = parts[3]
        self.stype_val = parts[4]
        self.sflags_val = parts[5]
        self.dummy_val = parts[6]
        print("[Parse] Assigned:", self.sid_val, self.ns_val, self.tsid_val, self.onid_val, self.stype_val,
              self.sflags_val, self.dummy_val)

    def _build_sid_line(self):
        return "%s:%s:%s:%s:%s:%s:%s" % (
            self.sid_val,
            self.ns_val,
            self.tsid_val,
            self.onid_val,
            self.stype_val,
            self.sflags_val,
            self.dummy_val
        )

    def toggleSidMode(self):
        self.sid_mode = 1 - self.sid_mode
        self.refreshList()

    def _build_pline_from_custom(self):
        # Sastavi: provider + (other tokens) + data pid + flags
        parts = []
        if self.custom_provider:
            parts.append(self.custom_provider.strip())
        for t in self.custom_other_tokens:
            if t:
                parts.append(t.strip())
        if self.custom_data_pid:
            parts.append(self.custom_data_pid.strip())
        if self.custom_caid:
            parts.append(self.custom_caid.strip())
        if self.custom_flags:
            parts.append(self.custom_flags.strip())
        # izbaci prazne
        parts = [p for p in parts if p]
        return ",".join(parts)

    def _cycle_flags(self, direction):
        cur = (self.custom_flags or "f:0").strip()
        if cur not in self.flags_options:
            # pokušaj da se normalizuje na f:n
            try:
                n = int(cur.split(":")[1])
                cur = "f:%d" % n
            except:
                cur = "f:0"
        if cur not in self.flags_options:
            cur = "f:0"

        idx = self.flags_options.index(cur)
        idx = (idx + direction) % len(self.flags_options)
        self.custom_flags = self.flags_options[idx]
        self.refreshList()

    def _cycle_caid(self, direction):
        cur = self.custom_caid or ""
        if cur not in self.caid_options:
            cur = ""
        idx = self.caid_options.index(cur)
        idx = (idx + direction) % len(self.caid_options)
        self.custom_caid = self.caid_options[idx]
        self.refreshList()

    # ----------------  Edit TP  ----------------
    def _edit_tp_field(self, idx, title, entrytype=2):  # 2 = NUMBER, 0 = TEXT
        if not self.edited_tp_params:
            self.session.open(MessageBox, "Nema TP podataka!", MessageBox.TYPE_INFO)
            return
        current = self.edited_tp_params[idx] if len(self.edited_tp_params) > idx else "0"
        self.session.openWithCallback(
            lambda val: self._tp_field_edited(idx, val),
            InputBox,
            title=title,
            text=current,
            type=entrytype  # Koristi integer: 2 za brojeve, 0 za tekst
        )

    def _tp_field_edited(self, idx, val):
        if val is not None and val.strip():
            while len(self.edited_tp_params) <= idx:
                self.edited_tp_params.append("0")
            self.edited_tp_params[idx] = val.strip()
            self.refreshList()

    # ---------------- Save & reload ----------------
    def keySave(self):
        if self.mode == "custom" and self.sid_mode == 1:
            self.ref = self._build_sid_line()  # ažuriraj ref iz custom polja
        try:
            ref_new = self.ref.strip()
            name_new = self.name.strip()
            if self.mode == "custom":
                pline_new = self._build_pline_from_custom().strip()
            else:
                pline_new = (self.pline or "").strip()

            if not self.original_ref:
                self.session.open(MessageBox, "Missing original ref!", MessageBox.TYPE_ERROR)
                return

            bak = self._update_service_entry(
                ref_old=self.original_ref,
                ref_new=ref_new,
                name_new=name_new,
                pline_new=pline_new
            )
            # Sačuvaj TP ako postoji i promenjen
            if self.tp_data and ':'.join(self.edited_tp_params) != self.original_tp_params:
                self._update_transponder_entry(
                    tp_key=self.tp_data['tp_key'],
                    new_params=':'.join(self.edited_tp_params),
                    prefix=self.tp_data['original_prefix']
                )

            self.session.open(
                MessageBox,
                "Saved!\nBackup: %s" % bak,
                MessageBox.TYPE_INFO,
                timeout=5
            )

            # Osveži i UI (DataBrowser) i E2 DB
            self.reloadE2DB()
            try:
                if self.parent and hasattr(self.parent, "reload"):
                    self.parent.reload()
            except:
                pass

        except Exception as e:
            self.session.open(MessageBox, "Save error:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def reloadE2DB(self):
        try:
            from enigma import eDVBDB
            db = eDVBDB.getInstance()
            if db:
                try:
                    db.reloadServicelist()
                except:
                    pass
                try:
                    db.reloadBouquets()
                except:
                    pass
            self["status"].setText("Reload DB: OK")
        except Exception as e:
            self["status"].setText("Reload DB error: %s" % str(e))

    # ---------------- lamedb IO helpers ----------------

    def _backup_path(self):
        return self.LAMEDB_PATH + ".bak_" + time.strftime("%Y%m%d_%H%M%S")

    def _read_lines_keep_nl(self):
        with open(self.LAMEDB_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines(True)  # keep \n

    def _write_atomic_with_backup(self, lines):
        bak = self._backup_path()

        # backup
        with open(bak, "w", encoding="utf-8", errors="ignore") as f:
            f.writelines(lines)

        tmp = "/etc/enigma2/.lamedb.tmp"
        with open(tmp, "w", encoding="utf-8", errors="ignore") as f:
            f.writelines(lines)

        os.rename(tmp, self.LAMEDB_PATH)
        return bak

    def _update_transponder_entry(self, tp_key, new_params, prefix='s'):
        lines = self._read_lines_keep_nl()
        in_trans = False
        current_key = None
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped == "transponders":
                in_trans = True
            elif stripped == "end":
                in_trans = False
            if in_trans:
                if ':' in stripped and len(stripped.split(':')) == 3:
                    current_key = stripped.upper()
                elif current_key == tp_key and stripped.startswith(('s ', 't ')):
                    lines[i] = f"{prefix} {new_params}\n"
                    break
        self._write_atomic_with_backup(lines)

    def _update_service_entry(self, ref_old, ref_new=None, name_new=None, pline_new=None):
        if not os.path.exists(self.LAMEDB_PATH):
            raise Exception("lamedb not found: %s" % self.LAMEDB_PATH)

        lines = self._read_lines_keep_nl()
        target = ref_old.strip()

        idx = None
        for i, ln in enumerate(lines):
            if ln.strip() == target:
                idx = i
                break
        if idx is None:
            raise Exception("Service ref not found in lamedb: %s" % target)

        if idx + 2 >= len(lines):
            raise Exception("Invalid lamedb structure around service (need 3 lines)")

        if ref_new is not None:
            lines[idx] = ref_new.rstrip("\n") + "\n"
        if name_new is not None:
            lines[idx + 1] = name_new.rstrip("\n") + "\n"
        if pline_new is not None:
            lines[idx + 2] = pline_new.rstrip("\n") + "\n"

        return self._write_atomic_with_backup(lines)


class AddFakeT2MIScreen(Setup):
    skin = """
    <screen name="AddFakeT2MIScreen" position="center,center" size="1800,900" title="..:: Add Fake T2MI Transponder/Service ::..">
        <widget name="config" position="40,60" size="1720,720" scrollbarMode="showOnDemand" font="Regular;26" />
        <widget name="key_red" position="120,840" size="320,40" backgroundColor="red" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
        <widget name="key_green" position="520,840" size="320,40" backgroundColor="green" font="Bold;24" foregroundColor="#000000" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, orbital_pos=390, default_freq=11778, default_sr=15155):
        self.skinName = "AddFakeT2MIScreen"
        Setup.__init__(self, session=session, setup="addfaket2mi")

        self.orbital_pos = orbital_pos

        # Config polja sa opcijom za tip kanala
        self.config_list = [
            ("Frequency (MHz)", ConfigInteger(default=default_freq, limits=(10000, 13000))),
            ("Symbol Rate (kSym/s)", ConfigInteger(default=default_sr, limits=(1000, 60000))),
            ("Polarization", ConfigSelection(default="0", choices=[("0", "H"), ("1", "V"), ("2", "L"), ("3", "R")])),
            ("FEC", ConfigSelection(default="3",
                                    choices=[("0", "Auto"), ("1", "1/2"), ("2", "2/3"), ("3", "3/4"), ("4", "5/6"),
                                             ("5", "7/8"), ("9", "9/10")])),
            ("System", ConfigSelection(default="1", choices=[("0", "DVB-S"), ("1", "DVB-S2")])),
            ("Modulation", ConfigSelection(default="1",
                                           choices=[("1", "QPSK"), ("2", "8PSK"), ("3", "QAM16"), ("4", "16APSK"),
                                                    ("5", "32APSK")])),
            ("T2MI PID", ConfigInteger(default=4096, limits=(0, 8192))),
            ("PLP", ConfigInteger(default=0, limits=(0, 255))),
            ("Channel Type", ConfigSelection(default="data", choices=[
                ("data", "Data (0x0C)"),
                ("tv_sd", "TV SD (0x01)"),
                ("tv_hd", "TV HD (0x19)")
            ])),
            ("Service Name", ConfigText(default="Service Name")),
            ("Provider", ConfigText(default="Povider")),
            ("Data PID (c:)", ConfigText(default="151000")),
            ("CAID (C:)",
             ConfigSelection(default="2600", choices=["", "2600 (BISS)", "0500", "0604", "0B00", "0D96", "181D"])),
            ("Flags (f:)", ConfigSelection(default="4", choices=[str(i) for i in range(0, 33)])),
        ]

        self.createConfigList(self.config_list)

        self["key_red"] = Button("Cancel")
        self["key_green"] = Button("Save")

        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
                                    {
                                        "cancel": self.close,
                                        "red": self.close,
                                        "ok": self.save,
                                        "green": self.save,
                                    }, -2)

    def createConfigList(self, entries):
        self.list = []
        for title, config_element in entries:
            self.list.append((title, config_element))
        self["config"].list = self.list
        self["config"].l.setList(self.list)

    def save(self):
        # Uzmi vrednosti iz config liste
        freq_mhz = int(self.config_list[0][1].value)
        sr_ksym = int(self.config_list[1][1].value)
        pol = self.config_list[2][1].value
        fec = self.config_list[3][1].value
        system = self.config_list[4][1].value
        mod = self.config_list[5][1].value
        t2mi_pid = int(self.config_list[6][1].value)
        plp = int(self.config_list[7][1].value)
        channel_type = self.config_list[8][1].value  # NOVO: tip kanala
        service_name = self.config_list[9][1].value.strip()
        provider = self.config_list[10][1].value.strip()
        data_pid = self.config_list[11][1].value.strip()
        caid = self.config_list[12][1].value.strip()
        flags = self.config_list[13][1].value

        # Mapiraj tip kanala na hex vrednost
        type_map = {
            "data": "0c",  # Data service
            "tv_sd": "01",  # TV SD
            "tv_hd": "19"  # TV HD
        }
        stype = type_map.get(channel_type, "0c")

        # Generiši TP key
        freq_hex = format(freq_mhz, '04x')
        ns_hex = f"0186{freq_hex}"
        tsid_hex = "03ea"
        onid_hex = "0000"

        tp_key = f"{ns_hex}:{tsid_hex}:{onid_hex}".upper()

        # Generiši TP params
        tp_params = (
            f"{freq_mhz * 1000}:{sr_ksym * 1000}:{pol}:{fec}:{self.orbital_pos}:"
            f"2:0:{system}:{mod}:0:2:255:0:0:0:{t2mi_pid}"
        )

        # Generiši service ref sa odgovarajućim tipom
        sid_hex = "03ea"
        sflags = "0"
        ref = f"{sid_hex}:{ns_hex}:{tsid_hex}:{onid_hex}:{stype}:{sflags}:0"

        # p: linija
        p_line = f"p:{provider},c:{data_pid}"
        if caid:
            p_line += f",C:{caid}"
        p_line += f",f:{flags}"

        # Preview tekst sa naznačenim tipom
        type_names = {"data": "Data", "tv_sd": "TV SD", "tv_hd": "TV HD"}
        preview_text = f"Transponder će biti dodat ({type_names.get(channel_type, 'Unknown')}):\n\n"
        preview_text += f"{tp_key}\n"
        preview_text += f"s {tp_params}\n"
        preview_text += f"/\n\n"
        preview_text += f"{ref}\n"
        preview_text += f"{service_name}\n"
        preview_text += f"{p_line}\n"

        # Sačuvaj podatke
        self.tp_key = tp_key
        self.tp_params = tp_params
        self.ref = ref
        self.service_name = service_name
        self.p_line = p_line

        # Otvori confirmation
        self.session.openWithCallback(
            self.confirmSave,
            ConfirmationPreviewScreen,
            preview_text=preview_text,
            tp_key=tp_key,
            tp_params=tp_params,
            ref=ref,
            name=service_name,
            p_line=p_line
        )

    def confirmSave(self, confirmed):
        if not confirmed:
            return

        try:
            lamedb_path = "/etc/enigma2/lamedb"

            with open(lamedb_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            transponder_insert_idx = None
            services_insert_idx = None

            i = 0
            while i < len(lines):
                line = lines[i].strip().lower()

                if line == "transponders":
                    i += 1
                    while i < len(lines):
                        if lines[i].strip().lower() == "end":
                            transponder_insert_idx = i
                            break
                        i += 1

                elif line == "services":
                    i += 1
                    while i < len(lines):
                        if lines[i].strip().lower() == "end":
                            services_insert_idx = i
                            break
                        i += 1
                i += 1

            if transponder_insert_idx is None or services_insert_idx is None:
                raise Exception("Nije pronađena transponder ili services sekcija u lamedb!")

            transponder_lines = [
                self.tp_key.lower() + "\n",
                "s " + self.tp_params + "\n",
                "/\n"
            ]

            services_lines = [
                self.ref.lower() + "\n",
                self.service_name + "\n",
                self.p_line + "\n"
            ]

            for line in reversed(services_lines):
                lines.insert(services_insert_idx, line)

            for line in reversed(transponder_lines):
                lines.insert(transponder_insert_idx, line)

            with open(lamedb_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            from enigma import eDVBDB
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()

            self.session.open(MessageBox, "Uspešno dodato u lamedb!\nReload izvršen.", MessageBox.TYPE_INFO, timeout=5)

            if self.parent and hasattr(self.parent, "reload"):
                self.parent.reload()

        except Exception as e:
            self.session.open(MessageBox, f"Greška pri dodavanju:\n{str(e)}", MessageBox.TYPE_ERROR)

        self.close()
        
class ConfirmationPreviewScreen(Screen):
    skin = """
    <screen name="ConfirmationPreviewScreen" position="center,center" size="1400,800" title="..:: Confirm Add to lamedb ::..">
        <widget name="preview" position="40,60" size="1320,680" font="Console;22" foregroundColor="white" backgroundColor="#1a1a1a" />
        <widget name="key_red" position="120,740" size="320,40" backgroundColor="red" font="Bold;24" foregroundColor="black" halign="center" valign="center" />
        <widget name="key_green" position="520,740" size="320,40" backgroundColor="green" font="Bold;24" foregroundColor="black" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, preview_text, tp_key, tp_params, ref, name, p_line):
        Screen.__init__(self, session)
        self.tp_key = tp_key
        self.tp_params = tp_params
        self.ref = ref
        self.name = name
        self.p_line = p_line

        self["preview"] = ScrollLabel(preview_text)
        self["key_red"] = Button("Cancel")
        self["key_green"] = Button("Save to lamedb")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
                                    {
                                        "cancel": self.closeCancel,
                                        "red": self.closeCancel,
                                        "ok": self.closeSave,
                                        "green": self.closeSave,
                                    }, -2)

    def closeCancel(self):
        self.close(False)

    def closeSave(self):
        self.close(True)

    def saveToLamedb(self):
        try:
            lamedb_path = "/etc/enigma2/lamedb"

            # Pročitaj ceo fajl
            with open(lamedb_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Pronađi pozicije za ubacivanje
            transponder_insert_idx = None
            services_insert_idx = None

            i = 0
            while i < len(lines):
                line = lines[i].strip().lower()

                if line == "transponders":
                    i += 1
                    while i < len(lines):
                        if lines[i].strip().lower() == "end":
                            transponder_insert_idx = i
                            break
                        i += 1

                elif line == "services":
                    i += 1
                    while i < len(lines):
                        if lines[i].strip().lower() == "end":
                            services_insert_idx = i
                            break
                        i += 1
                i += 1

            if transponder_insert_idx is None or services_insert_idx is None:
                raise Exception("Nije pronađena transponder ili services sekcija!")

            # BEZ PRAZNIH REDOVA
            transponder_lines = [
                self.tp_key.lower() + "\n",
                "s " + self.tp_params + "\n",
                "/\n"
            ]

            services_lines = [
                self.ref.lower() + "\n",
                self.name + "\n",
                self.p_line + "\n"
            ]

            # Ubaci od pozadine ka napred
            for line in reversed(services_lines):
                lines.insert(services_insert_idx, line)

            for line in reversed(transponder_lines):
                lines.insert(transponder_insert_idx, line)

            with open(lamedb_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            from enigma import eDVBDB
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()

            self.session.open(MessageBox, "Uspešno dodato u lamedb!\nReload izvršen.", MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, f"Greška pri dodavanju:\n{str(e)}", MessageBox.TYPE_ERROR)
        self.close()

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
        <widget name="key_white" position="1440,820" size="320,40" 
                backgroundColor="white" font="Bold;24" foregroundColor="#000000"  halign="center" valign="center" />
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
        self["key_green"] = Label("Astra.conf")
        self["key_yellow"] = Label("Astra-SM")
        self["key_blue"] = Label("Abertis")
        self["key_white"] = Label("Menu:Data Browser")
        self["background"] = Pixmap()
        self["snr_label"] = Label("SNR:")
        self["snr_bar"] = ProgressBar()
        self["agc_label"] = Label("AGC:")
        self["agc_bar"] = ProgressBar()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
                                    {
                                        "ok": self.close,
                                        "cancel": self.close,
                                        "red": self.close,
                                        "green": self.astraConfFunctions,
                                        "yellow": self.astraSmFunctions,
                                        "blue": self.abertisFunctions,
                                        "menu": self.openDataBrowser,   # NOVO
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
            ("4095 - c:150fff plp0", "t2mi://#t2mi_pid=4095&t2mi_plp=0&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp0"),
            ("4095 - c:150fff plp1", "t2mi://#t2mi_pid=4095&t2mi_plp=1&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp1"),
            ("4095 - c:150fff plp2", "t2mi://#t2mi_pid=4095&t2mi_plp=2&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp2"),
            ("4095 - c:150fff plp3", "t2mi://#t2mi_pid=4095&t2mi_plp=3&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp3"),
            ("4095 - c:150fff plp4", "t2mi://#t2mi_pid=4095&t2mi_plp=4&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp4"),
            ("4095 - c:150fff plp5", "t2mi://#t2mi_pid=4095&t2mi_plp=5&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp5"),
            ("4095 - c:150fff plp6", "t2mi://#t2mi_pid=4095&t2mi_plp=6&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp6"),
            ("4095 - c:150fff plp7", "t2mi://#t2mi_pid=4095&t2mi_plp=7&t2mi_input=http://127.0.0.1:8001/-----:", "4095_plp7"),
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
            "2025", "2026", "2027", "2028", "2035", "2036", "2037", "2038",
            "2050", "2060", "2270", "2271", "2272", "2273", "2274", "2281",
            "2282", "2283", "2284", "2302", "2303", "2305", "2306", "2308",
            "2520", "2521", "2522", "2523", "2524", "2531", "2532", "2533",
            "2534", "8000", "8001", "8002", "8003", "8004", "8005", "8006", "8008","8009"
        ]
        self.abertis_options = [(pid, f"http://127.0.0.1:9999/abertis/pid{pid}", pid) for pid in self.abertis_pids]
        self.astra_output = []
        self.analyzing = False
        self.astra_analyze_screen = None
        self.abertis_analyze_screen = None
        self.container = None

    def astraConfFunctions(self):
        """ChoiceBox za Astra.conf funkcije"""
        choices = [
            ("Create blanc astra.conf", "create_conf"),
            ("Add T2MI decap block", "add_t2mi_decap"),  # NOVO
            ("Add Abertis block", "add_abertis_block"),  # NOVO
            ("View astra.conf", "view_conf"),  # NOVO
            ("Reboot sistem", "reboot_system")
        ]
        self.session.openWithCallback(
            self.onAstraConfFunctionSelected,
            ChoiceBox,
            title=_("Astra.conf Functions"),
            list=choices
        )

    def astraSmFunctions(self):
        """ChoiceBox za Astra-SM funkcije"""
        choices = [
            ("Select Astra-SM Analyze option", "analyze_option"),
            ("Select Astra analyze log file", "select_log"),
            ("Select T2MI block from astra.conf", "select_t2mi_block"),
            ("Clear astra-sm log", "clear_logs")
        ]
        self.session.openWithCallback(
            self.onAstraSmFunctionSelected,
            ChoiceBox,
            title=_("Astra-SM Functions"),
            list=choices
        )

    def abertisFunctions(self):
        """ChoiceBox za Abertis funkcije"""
        choices = [
            ("Select Abertis PID", "select_pid"),
            ("Select Abertis log file", "select_abertis_log"),
            ("Select Abertis block from astra.conf", "select_abertis_block"),
            ("Clear Abertis log", "clear_abertis_logs")
        ]
        self.session.openWithCallback(
            self.onAbertisFunctionSelected,
            ChoiceBox,
            title=_("Abertis Functions"),
            list=choices
        )

    def onAstraConfFunctionSelected(self, choice):
        """Callback za Astra.conf funkcije"""
        if choice is None:
            return

        function_id = choice[1]
        if function_id == "create_conf":
            self.createAstraConf()
        elif function_id == "add_t2mi_decap":  # NOVO
            self.addT2MIDecapBlock()
        elif function_id == "add_abertis_block":  # NOVO
            self.addAbertisBlock()
        elif function_id == "view_conf":  # NOVO
            self.viewAstraConf()
        elif function_id == "reboot_system":
            self.rebootSystem()

    def onAstraSmFunctionSelected(self, choice):
        """Callback za Astra-SM funkcije"""
        if choice is None:
            return
            
        function_id = choice[1]
        if function_id == "analyze_option":
            self.startAstraAnalyze()
        elif function_id == "select_log":
            self.selectAstraLogFile()
        elif function_id == "select_t2mi_block":
            self.selectT2MIBlock()
        elif function_id == "clear_logs":
            self.clearAstraLogs()

    def onAbertisFunctionSelected(self, choice):
        """Callback za Abertis funkcije"""
        if choice is None:
            return
            
        function_id = choice[1]
        if function_id == "select_pid":
            self.startAbertisAnalyze()
        elif function_id == "select_abertis_log":
            self.selectAbertisLogFile()
        elif function_id == "select_abertis_block":
            self.selectAbertisBlock()
        elif function_id == "clear_abertis_logs":
            self.clearAbertisLogs()

    def rebootSystem(self):
        """Reboot sistem"""
        self.session.openWithCallback(
            self.confirmReboot,
            MessageBox,
            _("Are you sure you want to reboot the system?"),
            MessageBox.TYPE_YESNO
        )

    def addT2MIDecapBlock(self):
        """Dodavanje T2MI decap bloka"""
        self.session.open(T2MIDecapConfigScreen, self)

    def addAbertisBlock(self):
        """Dodavanje Abertis bloka (za sada placeholder)"""
        self.session.open(MessageBox, _("Abertis block function will be implemented soon"), MessageBox.TYPE_INFO)

    def viewAstraConf(self):
        """Pregled astra.conf fajla - orijentisan na levu stranu"""
        conf_path = "/etc/astra/astra.conf"
        if os.path.exists(conf_path):
            try:
                with open(conf_path, "r") as f:
                    content = f.read()

                # Kreiraj custom screen za prikaz sa levom orijentacijom
                self.session.open(AstraConfViewScreen, content)
            except Exception as e:
                self.session.open(MessageBox, _("Error reading astra.conf: ") + str(e), MessageBox.TYPE_ERROR)
        else:
            self.session.open(MessageBox, _("astra.conf not found!"), MessageBox.TYPE_ERROR)

    def createAstraConf(self):
        """Kreiranje osnovnog astra.conf fajla"""
        try:
            conf_path = "/etc/astra/astra.conf"
            os.makedirs(os.path.dirname(conf_path), exist_ok=True)

            # Osnovni template
            basic_conf = """-- Astra configuration file
    -- Generated by Ciefp Satellite Analyzer

    -- Basic settings
    dvb_scan = true
    http_port = 9999

    -- Add your T2MI and Abertis blocks below:

    """
            with open(conf_path, "w") as f:
                f.write(basic_conf)

            self.session.open(MessageBox, _("Basic astra.conf created!"), MessageBox.TYPE_INFO)

        except Exception as e:
            self.session.open(MessageBox, _("Error creating astra.conf: ") + str(e), MessageBox.TYPE_ERROR)

    def confirmReboot(self, result):
        """Potvrda za reboot"""
        if result:
            import os
            os.system("reboot")

    def selectAstraLogFile(self):
        """Selektovanje Astra log fajla za T2MI"""
        self.createBouquetWithType("t2mi")

    def selectAbertisLogFile(self):
        """Selektovanje Abertis log fajla"""
        self.createBouquetWithType("abertis")

    def createBouquetWithType(self, log_type):
        """Kreiranje buketa sa određenim tipom"""
        print(f"[SatelliteAnalyzer] Starting {log_type} bouquet creation")
        log_dir = "/tmp/CiefpSatelliteAnalyzer"
        if not os.path.exists(log_dir):
            self.session.open(MessageBox, _("Log directory not found!"), MessageBox.TYPE_ERROR)
            return

        # Filtriraj log fajlove po tipu - NOVI NAZIVI
        if log_type == "t2mi":
            pattern = "t2mi_*.log"
        else:  # abertis
            pattern = "abertis_*.log"

        import glob
        log_files = glob.glob(os.path.join(log_dir, pattern))
        logs = [os.path.basename(f) for f in log_files]

        if not logs:
            self.session.open(MessageBox, _(f"No {log_type} log files found!"), MessageBox.TYPE_ERROR)
            return

        choices = []
        for log in sorted(logs):
            # Prikaži lepši naziv u ChoiceBox-u
            display_name = log.replace('.log', '')
            choices.append((display_name, (log, log_type)))

        self.session.openWithCallback(
            self.logSelected,
            ChoiceBox,
            title=f"Select {log_type.upper()} analyze log file",
            list=choices
        )

    def selectT2MIBlock(self):
        """Selektovanje T2MI blocka iz astra.conf"""
        self.session.open(MessageBox, _("Please use 'Select Astra analyze log file' to select T2MI blocks"), MessageBox.TYPE_INFO)

    def selectAbertisBlock(self):
        """Selektovanje Abertis blocka iz astra.conf"""
        self.session.open(MessageBox, _("Please use 'Select Abertis log file' to select Abertis blocks"), MessageBox.TYPE_INFO)

    def clearAstraLogs(self):
        """Brisanje T2MI logova"""
        self.clearLogs("t2mi")

    def clearAbertisLogs(self):
        """Brisanje Abertis logova"""
        self.clearLogs("abertis")

    def clearLogs(self, log_type):
        """Opšta funkcija za brisanje logova"""
        import glob
        log_dir = "/tmp/CiefpSatelliteAnalyzer"

        # Koristimo nove nazive
        if log_type == "t2mi":
            pattern = "t2mi_*.log"
        else:  # abertis
            pattern = "abertis_*.log"

        log_files = glob.glob(os.path.join(log_dir, pattern))
        if not log_files:
            self.session.open(MessageBox, _(f"No {log_type} log files found to delete"), MessageBox.TYPE_INFO)
            return

        deleted_count = 0
        for log_file in log_files:
            try:
                os.remove(log_file)
                deleted_count += 1
                print(f"[SatelliteAnalyzer] Deleted: {os.path.basename(log_file)}")
            except Exception as e:
                print(f"Error deleting {log_file}: {e}")

        self.session.open(MessageBox, _(f"Deleted {deleted_count} {log_type} log files"), MessageBox.TYPE_INFO)

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

    def openDataBrowser(self):
        # orbital_position već koristiš na više mesta (frontendInfo.getAll(True)) :contentReference[oaicite:3]{index=3}
        orbital_pos = 0
        service = self.session.nav.getCurrentService()
        if service:
            frontendInfo = service.frontendInfo()
            if frontendInfo:
                data = frontendInfo.getAll(True)
                orbital_pos = int(data.get("orbital_position", 0) or 0)

        self.session.open(DataBrowserScreen, self, orbital_pos)

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
        return {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "5/6", 5: "7/8", 6: "8/9", 7: "3/5", 8: "4/5", 9: "9/10"}.get(fec, "N/A")

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
        import re, os, urllib
        from enigma import eDVBDB

        log_path = os.path.join("/tmp/CiefpSatelliteAnalyzer", log_file)
        if not os.path.exists(log_path):
            self.session.open(MessageBox, _("Selected log file not found!"), MessageBox.TYPE_ERROR)
            return

        blocks = self.parse_astra_conf()

        # Detect type by filename
        if log_file.startswith("t2mi_"):
            log_type = "t2mi"
        elif log_file.startswith("abertis_"):
            log_type = "abertis"
        else:
            log_type = "abertis" if "abertis" in log_file else "t2mi"

        # Validate block
        if block_ref not in blocks[log_type] or not blocks[log_type][block_ref]["output"]:
            self.session.open(MessageBox, _(f"Selected {log_type} block not found in astra.conf!"), MessageBox.TYPE_ERROR)
            return

        matched = blocks[log_type][block_ref]
        base_url = matched["output"]
        marker_pid = matched["pid"]
        provider_name = matched["name"]

        # Detect satellite position
        satellite = "Unknown"
        service = self.session.nav.getCurrentService()
        if service:
            frontendInfo = service.frontendInfo()
            if frontendInfo:
                frontendData = frontendInfo.getAll(True)
                if frontendData:
                    try:
                        orbital_pos = frontendData.get("orbital_position", 0)
                        satellite = self.formatOrbitalPos(orbital_pos)
                    except:
                        pass

        # Parse log file into channels
        tv_channels = []
        radio_channels = []
        sid = name = provider = None

        with open(log_path, "r") as f:
            for line in f:
                if 'sid:' in line:
                    sid_match = re.search(r'sid:\s*(\d+)', line)
                    if sid_match:
                        sid = sid_match.group(1)

                elif 'Service:' in line:
                    svc = re.search(r'Service:\s*(.+)', line)
                    if svc:
                        name = svc.group(1).strip()

                elif 'Provider:' in line and sid and name:
                    prov = re.search(r'Provider:\s*(.*)', line)
                    provider = prov.group(1).strip() if prov else "Unknown"

                    radio_keywords = ["RADIO", "FM", "RNE", "COPE", "SER", "ONDA", "MELODIA"]
                    is_radio = any(k in name.upper() for k in radio_keywords)
                    ch_type = "RADIO" if is_radio else "TV"

                    channel_data = {
                        "sid": int(sid),
                        "name": name,
                        "provider": provider,
                        "type": ch_type,
                        "pid": marker_pid,
                        "url": base_url
                    }

                    if ch_type == "TV":
                        tv_channels.append(channel_data)
                    else:
                        radio_channels.append(channel_data)

                    sid = name = provider = None

        # Sort channels: TV first, then Radio
        new_channels = tv_channels + radio_channels

        if not new_channels:
            self.session.open(MessageBox, _("No channels found in selected log!"), MessageBox.TYPE_ERROR)
            return

        # Bouquet path + marker template
        if log_type == "t2mi":
            bouquet_path = "/etc/enigma2/userbouquet.buket_t2mi.tv"
            marker_template = ":: T2Mi :: {provider} :: pid {pid} :: Satellite {satellite} ::"
        else:
            bouquet_path = "/etc/enigma2/userbouquet.buket_abertis.tv"
            marker_template = "##### Abertis PID {pid} #####"

        # URL correction function
        def encode_abertis_url(url):
            url = url.replace(":", "%3a")
            url = url.replace("%3a//", "%3a//")  # keep //
            return url

        marker_text = marker_template.format(
            pid=marker_pid,
            provider=provider_name,
            satellite=satellite
        )

        # --- FIX: Add line break BEFORE append if file is not empty ---
        if os.path.exists(bouquet_path) and os.path.getsize(bouquet_path) > 0:
            if os.path.getsize(bouquet_path) > 0:
                last = ""
                with open(bouquet_path, "rb") as r:
                    r.seek(-1, os.SEEK_END)
                    last = r.read(1)

                # Dodaj novi red SAMO ako poslednja linija NE završava sa \n
                if last != b'\n':
                    with open(bouquet_path, "a") as f:
                        f.write("\n")

        # --- APPEND marker + channels ---
        with open(bouquet_path, "a") as f:

            # Marker
            f.write(f'#SERVICE 1:64:1F:0:0:0:0:0:0:0::{marker_text}\n')
            f.write(f'#DESCRIPTION {marker_text}\n')

            # Channels for this PID
            for ch in new_channels:
                service_type = "1" if ch["type"] == "TV" else "2"
                url_enc = encode_abertis_url(ch["url"])

                # Za T2MI kanale koristimo samo ime kanala, bez (TV) i (PID)
                if log_type == "t2mi":
                    f.write(
                        f'#SERVICE 1:0:{service_type}:{ch["sid"]:X}:3157:{int(ch["pid"]):X}:0:0:0:0:{url_enc}:{ch["name"]}\n'
                    )
                    f.write(
                        f'#DESCRIPTION {ch["name"]}\n'
                    )
                # Za Abertis kanale zadržavamo originalni format
                else:
                    f.write(
                        f'#SERVICE 1:0:{service_type}:{ch["sid"]:X}:3157:{int(ch["pid"]):X}:0:0:0:0:{url_enc}:({ch["type"]}) {ch["name"]} ({ch["pid"]})\n'
                    )
                    f.write(
                        f'#DESCRIPTION ({ch["type"]}) {ch["name"]} ({ch["pid"]})\n'
                    )

        # Osveži bukete
        eDVBDB.getInstance().reloadBouquets()
        self.session.openWithCallback(
            lambda x: None,
            MessageBox,
            _(f"{log_type.upper()} bouquet created/updated and reloaded successfully!"),
            MessageBox.TYPE_INFO,
            timeout=10,
            default=True
        )

