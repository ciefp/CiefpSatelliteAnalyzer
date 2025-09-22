# plugin.py
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Plugins.Extensions.CiefpSatelliteAnalyzer.CiefpSatelliteAnalyzer import SatelliteAnalyzer


PLUGIN_VERSION = "1.4"

def main(session, **kwargs):
    session.open(SatelliteAnalyzer)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="CiefpSatelliteAnalyzer",
        description=f"Show all information about the current channel (Version {PLUGIN_VERSION})",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="satellite.png",
        fnc=main,
    )