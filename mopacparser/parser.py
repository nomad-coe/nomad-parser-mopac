# Copyright 2016-2018 Mikkel Strange, Fawzi Mohamed, Ankit Kariryaa
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#from builtins import object
import setup_paths
from nomadcore.simple_parser import SimpleMatcher as SM, mainFunction
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
import os
import sys
import json


class MopacContext(object):
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

# section_single_configuration_calculation
sm_etot = SM(r"\s*TOTAL ENERGY\s*=\s*(?P<energy_total>[-+0-9.eEdD]+)\s*EV")
sm_eigenvalues = SM(name='Eigenvalues',
                    startReStr=r"\s*EIGENVALUES",
                    endReStr=r"\s*NET ATOMIC CHARGES",
                    sections=['section_eigenvalues'],
                    subMatchers=[
                        SM(r"\s*(?P<eigenvalues_values>[-+0-9.eEdD]+)",
                           repeats=True)
                    ])

sm_energies = SM(name='Energies',
                 startReStr=r"\s*SCF FIELD WAS ACHIEVED",
                 sections=['section_single_configuration_calculation'],
                 subMatchers=[sm_etot, sm_eigenvalues])

# section_method

# section_system

# section_run
#   program_information
sm_version = SM(r"\s*\**\s*Version\s*(?P<program_version>[0-9a-zA-Z_.]*)")
sm_header = SM(name='ProgramHeader',
               startReStr=r"\s*\**\s*Cite this work as:\s*\**",
               subMatchers=[sm_version])

sm_run = SM(name='newRun',
            startReStr=r"",
            #forwardMatch=True,
            required=True,
            fixedStartValues={'program_name': 'mopac'},
            sections=['section_run'],
            subMatchers=[sm_header,
                         sm_energies
                        ])

mainFileDescription = \
    SM(name='root',
       weak=True,
       forwardMatch=True,
       startReStr=r"",
       subMatchers=[sm_run])

# loading metadata from nomad-meta-info/meta_info/nomad_meta_info/fhi_aims.nomadmetainfo.json

parserInfo = {
  "name": "mopac_parser",
  "version": "1.0"
}

class MopacParser():
    """ A proper class envolop for running this parser from within python. """
    def __init__(self, backend, **kwargs):
        self.backend_factory = backend

    def parse(self, mainfile):
        from unittest.mock import patch
        logging.info('mopac parser started')
        logging.getLogger('nomadcore').setLevel(logging.WARNING)
        backend = self.backend_factory("mopac.nomadmetainfo.json")
        context = MopacContext()
        with patch.object(sys, 'argv', ['<exe>', '--uri', 'nmd://uri', mainfile]):
            mainFunction(
                mainFileDescription,
                None,
                parserInfo,
                cachingLevelForMetaName=dict(),
                superContext=context,
                superBackend=backend)

        return backend


if __name__ == "__main__":
    metaInfoPath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../nomad-meta-info/meta_info/nomad_meta_info/mopac.nomadmetainfo.json"))
    metaInfoEnv, warnings = loadJsonFile(filePath=metaInfoPath, dependencyLoader=None, extraArgsHandling=InfoKindEl.ADD_EXTRA_ARGS, uri=None)

    superContext = MopacContext()
    mainFunction(mainFileDescription, metaInfoEnv, parserInfo, superContext=superContext)
