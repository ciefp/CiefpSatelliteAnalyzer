# CiefpSatelliteAnalyzer.py
from enigma import eServiceCenter, eServiceReference, iServiceInformation, eTimer
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Screens.Screen import Screen
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap
from Components.ProgressBar import ProgressBar
import os
import xml.etree.ElementTree as ET


class SatelliteAnalyzer(Screen):
    skin = """
    <screen name="SatelliteAnalyzer" position="center,center" size="1800,900" title="..:: Ciefp Satellite Analyzer ::..">
        <!-- Pozadina desno -->
        <eLabel position="1400,0" size="400,900" backgroundColor="#0D1B36" zPosition="-1" />
        <!-- Logo (400x400) -->
        <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer/background.png" position="1400,0" size="400,400" />
        <!-- Naslov -->
        <widget source="Title" render="Label" position="1400,420" size="400,50" 
                font="Regular;30" halign="center" valign="center" foregroundColor="white" backgroundColor="#0D1B36" />
        <!-- Vrijeme -->
        <widget name="time" position="1400,480" size="400,40" 
                font="Regular;24" halign="center" valign="center" foregroundColor="#BBBBBB" backgroundColor="#0D1B36" />
        <!-- Dugmad -->
        <widget name="key_red" position="1440,540" size="320,40" 
                backgroundColor="red" font="Regular;24" halign="center" valign="center" />
        <widget name="key_green" position="1440,600" size="320,40" 
                backgroundColor="green" font="Regular;24" halign="center" valign="center" />
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
        self["time"] = Label("")
        self["key_red"] = Label("Back")
        self["key_green"] = Label("Update")
        self["background"] = Pixmap()

        # Trake
        self["snr_label"] = Label("SNR:")
        self["snr_bar"] = ProgressBar()
        self["agc_label"] = Label("AGC:")
        self["agc_bar"] = ProgressBar()

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "red": self.close,
                "green": self.updateInfo,
                "up": self["info_left"].pageUp,
                "down": self["info_left"].pageDown,
            }, -2)

        # Tajmer za vreme
        self.time_update_timer = eTimer()
        self.time_update_timer.callback.append(self.updateTime)
        self.time_update_timer.start(1000)
        self.onClose.append(self.time_update_timer.stop)

        # Tajmer za signal
        self.signal_update_timer = eTimer()
        self.signal_update_timer.callback.append(self.updateAllInfo)
        self.signal_update_timer.start(5000)
        self.onClose.append(self.signal_update_timer.stop)

        self.onLayoutFinish.append(self.updateInfo)

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
                    print(f"[SatelliteAnalyzer] Sirovi frontend podaci: {frontendData}")
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
                        f"[SatelliteAnalyzer] Frontend podaci: SNR_DB={snr_db}, SNR_PERCENT={snr_percent}, BER={ber}, AGC={agc}, Crypted={is_crypted}, SID={sid}, TSID={tsid}, ONID={onid}")
                    return snr_db, snr_percent, ber, agc, is_crypted, sid, tsid, onid
                except Exception as e:
                    print(f"[SatelliteAnalyzer] Greška pri dohvatanju signala iz frontend-a: {e}")
        return 0.0, 0, 0, 0, 0, 0, 0, 0

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
            0x0664: "Irdeto",
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
        return {0:"Auto",1:"1/2",2:"2/3",3:"3/4",4:"4/5",5:"5/6",7:"7/8",8:"8/9",9:"9/10"}.get(fec, "N/A")

    def getModulation(self, mod):
        return {0:"Auto",1:"QPSK",2:"8PSK",3:"64QAM",4:"16APSK",5:"32APSK"}.get(mod, "N/A")

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
        return {0:"H",1:"V",2:"L",3:"R"}.get(pol, "N/A")

    # Nove metode za DVB-T specifične parametre
    def getBandwidth(self, bw):
        return {6000000: "6 MHz", 7000000: "7 MHz", 8000000: "8 MHz"}.get(bw, f"{bw/1000000} MHz")

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

        try:
            name = info.getName() or "N/A"
        except:
            name = "N/A"
        try:
            provider = info.getInfoString(iServiceInformation.sProvider) or "N/A"
        except:
            provider = "N/A"

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
            pls_mode_str = {0:"Root",1:"Gold",2:"Combo"}.get(pls_mode, str(pls_mode))
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
            vpid = info.getInfo(iServiceInformation.sVideoPID)
            vpid_str = f"0x{vpid:X}" if vpid != -1 else "Nema"
        except:
            vpid_str = "Nema"
        try:
            apid = info.getInfo(iServiceInformation.sAudioPID)
            apid_str = f"0x{apid:X}" if apid != -1 else "Nema"
        except:
            apid_str = "Nema"
        try:
            pcrpid = info.getInfo(iServiceInformation.sPCRPID)
            pcr_str = f"0x{pcrpid:X}" if pcrpid != -1 else "Nema"
        except:
            pcr_str = "Nema"
        try:
            pmtpid = info.getInfo(iServiceInformation.sPMTPID)
            pmt_str = f"0x{pmtpid:X}" if pmtpid != -1 else "Nema"
        except:
            pmt_str = "Nema"
        try:
            txt_pid = info.getInfo(iServiceInformation.sTXTPID)
            txt_str = f"0x{txt_pid:X}" if txt_pid != -1 else "Nema"
        except:
            txt_str = "Nema"

        # DVB-T specifični parametri
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

        # --- SIGNAL INFO ---
        frontendInfo = service.frontendInfo()
        frontendData = frontendInfo and frontendInfo.getAll(True)
        try:
            snr_db = frontendData.get("tuner_signal_quality_db", 0) / 100.0
            snr_percent = frontendData.get("tuner_signal_quality", 0) // 655
            ber = frontendData.get("tuner_bit_error_rate", 0)
            agc = frontendData.get("tuner_signal_power", 0) // 655
        except:
            snr_db, snr_percent, ber, agc = 0.0, 0, 0, 0

        # --- SI/TS/ONID ---
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
            f"   ONID: 0x{onid:04X}"
        ]
        return "\n".join(right_text)