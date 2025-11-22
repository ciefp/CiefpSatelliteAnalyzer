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
        self["key_green"] = Label("Astra.conf")
        self["key_yellow"] = Label("Astra-SM")
        self["key_blue"] = Label("Abertis")
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
                                        "green": self.astraConfFunctions,
                                        "yellow": self.astraSmFunctions,
                                        "blue": self.abertisFunctions,
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

