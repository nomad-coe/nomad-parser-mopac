#from builtins import object
import setup_paths
from nomadcore.simple_parser import SimpleMatcher as SM, mainFunction
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
import os
import sys
import json


class SampleContext(object):
    """context for the sample parser"""

    def __init__(self):
        self.parser = None

    def initialize_values(self):
        """allows to reset values if the same superContext is used
        to parse different files"""
        pass

    def startedParsing(self, path, parser):
        """called when parsing starts"""
        self.parser = parser
        # allows to reset values if the same superContext
        # is used to parse different files
        self.initialize_values()

# description of the input
mainFileDescription = \
    SM(name='root',
        weak=True,
        startReStr="",
        subMatchers=[
        SM(name='newRun',
           startReStr=r"\*",
           repeats=True,
           required=True,
           forwardMatch=True,
           sections=['section_run'],
           subMatchers=[
           SM(name='SinglePointEvaluation',
              startReStr=r"\s*FINAL HEAT OF FORMATION",
              repeats=False,
              forwardMatch=True,
              sections=['section_single_configuration_calculation'],
              subMatchers=[
              SM(r"\s*TOTAL ENERGY\s*=\s*(?P<energy_total>[-+0-9.eEdD]+)\s*EV")])
                ])
              ])

# loading metadata from nomad-meta-info/meta_info/nomad_meta_info/fhi_aims.nomadmetainfo.json

parserInfo = {
  "name": "mopac_parser",
  "version": "1.0"
}

metaInfoPath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../nomad-meta-info/meta_info/nomad_meta_info/mopac_parser.nomadmetainfo.json"))
metaInfoEnv, warnings = loadJsonFile(filePath=metaInfoPath, dependencyLoader=None, extraArgsHandling=InfoKindEl.ADD_EXTRA_ARGS, uri=None)

if __name__ == "__main__":
    superContext = SampleContext()
    mainFunction(mainFileDescription, metaInfoEnv, parserInfo, superContext=superContext)
