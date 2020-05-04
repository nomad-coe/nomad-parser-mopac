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

from __future__ import division
import os
from contextlib import contextmanager
import numpy as np
from nomadcore.unit_conversion.unit_conversion import convert_unit as cu
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from .reader import Reader
import logging


@contextmanager
def open_section(p, name):
    gid = p.openSection(name)
    yield gid
    p.closeSection(name, gid)


def c(value, unit=None):
    """ Dummy function for unit conversion"""
    return cu(value, unit)


parser_info = {"name": "parser_mopac", "version": "1.0"}

def parse(filename, backend):
    p = backend
    o = open_section
    r = Reader(filename)
    p.startedParsingSession(filename, parser_info)

    with o(p, 'section_run'):
        p.addValue('program_name', 'MOPAC')
        p.addValue('program_version', r.program_version)
        with o(p, 'section_system') as system_gid:
            p.addArrayValues('atom_labels', r.atom_labels)
            p.addArrayValues('atom_positions', c(r.atom_positions,
                                                 'angstrom'))
            pbc = np.array((0, 0, 0), bool)
            p.addArrayValues('configuration_periodic_dimensions', pbc)
            if 'number_of_electrons' in r:
                p.addArrayValues('number_of_electrons', r.number_of_electrons)
        with o(p, 'section_sampling_method'):
            p.addValue('ensemble_type', 'NVE')
        with o(p, 'section_frame_sequence'):
            pass
        with o(p, 'section_method') as method_gid:
            p.addValue('x_mopac_method', r.x_mopac_method)
            p.addValue('x_mopac_keyword_line', r.inp_parm_line)
            p.addRealValue('total_charge', r.total_charge)
#            p.addValue('scf_threshold_energy_change',
#                       c(r.scf_threshold_energy_changer, 'hartree'))
            if 'spin_target_multiplicity' in r:
                p.addRealValue('spin_target_multiplicity',
                               r.spin_target_multiplicity)
        with o(p, 'section_single_configuration_calculation'):
            p.addValue('single_configuration_calculation_to_system_ref',
                       system_gid)
            p.addValue('single_configuration_to_calculation_method_ref',
                       method_gid)
            p.addRealValue('energy_total', c(r.energy_total, 'eV'))
            if 'x_mopac_fhof' in r:
                p.addRealValue('x_mopac_fhof', c(r.x_mopac_fhof, 'eV'))
            if 'electronic_kinetic_energy' in r:
                p.addRealValue('electronic_kinetic_energy',
                               c(r.electronic_kinetic_energy, 'eV'))
            if 'atom_forces' in r:
                p.addArrayValues('atom_forces',
                                 c(r.atom_forces, 'eV/angstrom'))
            if 'energy_reference_highest_occupied' in r:
                p.addArrayValues('energy_reference_highest_occupied',
                               c(r.energy_reference_highest_occupied, 'eV'))
            if 'spin_S2' in r:
                p.addRealValue('spin_S2', r.spin_S2)

            if 'time_calculation' in r:
                p.addRealValue('time_calculation', r.time_calculation)

            with o(p, 'section_eigenvalues'):
                if 'eigenvalues_values' in r:
                    p.addValue('eigenvalues_kind', 'normal')
                    p.addArrayValues('eigenvalues_values',
                                     c(r.eigenvalues_values, 'eV'))
                    p.addArrayValues('eigenvalues_kpoints',
                                     r.eigenvalues_kpoints)
                if 'eigenvalues_occupation' in r:
                    p.addArrayValues('eigenvalues_occupation',
                                     r.eigenvalues_occupation)

    p.finishedParsingSession("ParseSuccess", None)


class MopacParser():
    """ A proper class envolop for running this parser from within python. """
    def __init__(self, backend, **kwargs):
        self.backend_factory = backend

    def parse(self, mainfile):
        logging.info('mopac parser started')
        logging.getLogger('nomadcore').setLevel(logging.WARNING)
        backend = self.backend_factory("mopac.nomadmetainfo.json")
        parse(mainfile, backend)
        return backend


if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    parse(filename)
