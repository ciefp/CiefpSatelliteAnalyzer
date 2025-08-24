# plugin.py
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Plugins.Extensions.CiefpSatelliteAnalyzer.CiefpSatelliteAnalyzer import SatelliteAnalyzer


PLUGIN_VERSION = "1.0"

def main(session, **kwargs):
    session.open(SatelliteAnalyzer)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="CiefpSatelliteAnalyzer",
        description=f"Prikaži sve informacije o trenutnom kanalu (Version {PLUGIN_VERSION})",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="satellite.png",
        fnc=main,
    )