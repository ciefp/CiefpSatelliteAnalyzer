# plugin.py
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Plugins.Extensions.CiefpSatelliteAnalyzer.CiefpSatelliteAnalyzer import SatelliteAnalyzer


PLUGIN_VERSION = "1.8"

def main(session, **kwargs):
    session.open(SatelliteAnalyzer)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="CiefpSatelliteAnalyzer",
        description=f"ASTRA-SM Analyze T2Mi and Abertis services (Version {PLUGIN_VERSION})",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="satellite.png",
        fnc=main,
    )