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

import numpy as np
from ase import Atoms
from ase import units
import re


class Reader:
    methods = ['AM1', 'MNDO', 'MNDOD', 'PM3', 'PM6', 'PM6-D3', 'PM6-DH+',
               'PM6-DH2', 'PM6-DH2X', 'PM6-D3H4', 'PM6-D3H4X', 'PMEP', 'PM7',
               'PM7-TS', 'RM1']

    multiplicities = {'singlet': 1, 'doublet': 2, 'triplet': 3, 'quartet': 4,
                      'quintet': 5, 'sextet': 6, 'septet': 7, 'octet': 8,
                      'nonet': 9}

    def __init__(self, filename):

        self.unit2ase = {  # convert to ase units (eV, Angstrom)
            'ev': units.eV,
            'kcal/mol': units.kcal / units.mol,
            'kj/mol': units.kJ / units.mol,
            'hartree': units.Hartree,
            'kcal/angstrom': units.kcal / units.mol / units.Angstrom,
        }

        with open(filename, 'r') as f:
            self.lines = f.readlines()

        self.data = {}
        self.restrs = {
            'program_version':
            re.compile(r"\s*Version\s*(?P<program_version>[0-9.a-zA-Z]+)\s+"),
            'natoms':
            re.compile(r"\s*Empirical\s*Formula:.*=\s*(?P<natoms>[0-9]+)"),
            'positions_begin':
            re.compile(r"\s*CARTESIAN\s*COORDINATES"),
            'energy_total':
            re.compile(r"\s*TOTAL\s*ENERGY\s*=\s*(?P<energy_total>[0-9.+-]+)\s*(?P<unit>[a-zA-Z]+)"),
            'x_mopac_fhof':  # final heat of formation
            re.compile(r"FINAL\s*HEAT\s*OF\s*FORMATION\s*=\s*(?P<x_mopac_fhof>[0-9-.+-]+)\s*(?P<unit>[A-Z/]+)\s*="),
            'forces_begin':
            re.compile(r"\s*FINAL\s*POINT\s*AND\s*DERIVATIVES"),
            'eigenvalues_begin':
            re.compile(r"\s*EIGENVALUES"),
            'n_filled':
            re.compile(r"NO.\s*OF\s*FILLED\s*LEVELS\s*=\s*(?P<n_filled>[0-9]+)"),
            'n_alpha':
            re.compile(r"NO.\s*OF\s*ALPHA\s*ELECTRONS\s*=\s*(?P<n_alpha>[0-9]+)"),
            'n_beta':
            re.compile(r"NO.\s*OF\s*BETA\s*ELECTRONS\s*=\s*(?P<n_beta>[0-9]+)"),
            'spin_S2':
            re.compile(r"\(S\*\*2\)\s*=\s*(?P<spin_S2>[0-9.]+)"),
            'time_calculation':
            re.compile(r"TOTAL\s*JOB\s*TIME:\s*(?P<time_calculation>[0-9.]+)\s*"),
            'total_charge':
            re.compile(r"\s*\**\s*CHARGE\s*ON\s*SYSTEM\s*=\s*(?P<total_charge>[0-9]+)")

        }
        self.read()
        self.calculate_and_transform()

    def rep2bl(self, j, fun=float):
        """ Loop until a blank line is found, starting from line j.
            Parameters:
                j: starting line
                fun: [fun(x) for x in line.split()]
        """
        x = []
        while not self.lines[j].isspace():  # continue until a blank line
            x += [fun(e) for e in self.lines[j].split()]
            j += 1
        return x

    def get_index(self, pattern, istart=0, istop=None):
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        lines = self.lines[istart:istop]
        for i, line in enumerate(lines):
            m = re.search(pattern, line)
            if m:
                break
        return istart + i

    def get_input_parameter_line(self):
        i = self.get_index(r"\s*\*\s*CALCULATION DONE:")
        j = self.get_index(r"\s*\*{3,}", istart=i)
        return self.lines[j + 1]

    def get_natoms(self):
        natoms = None
        for line in self.lines:
            m = re.search(self.restrs['natoms'],
                          line)
            if m:
                natoms = int(m.group('natoms'))
                break
        assert natoms
        return natoms

    def read(self):
        natoms = self.get_natoms()
        self.data['natoms'] = natoms
        self.data['inp_parm_line'] = self.get_input_parameter_line().rstrip()

        for i, line in enumerate(self.lines):
            # program_version
            if self.data.get('program_version') is None:
                m = re.search(self.restrs['program_version'], line)
                if m:
                    self.data['program_version'] = m.group('program_version')

            if self.data.get('total_charge') is None:
                m = re.search(self.restrs['total_charge'], line)
                if m:
                    self.data['total_charge'] = int(m.group('total_charge'))

            # atom_positions, atom_labels
            if self.data.get('atom_positions') is None:
                m = re.search(self.restrs['positions_begin'], line)
                if m:
                    if 'ATOM' not in self.lines[i + 2]:
                        begin = 2
                        symbols = []
                        positions = []
                        for l in self.lines[i + begin: i + begin + natoms]:
                            vals = l.split()
                            symbols.append(vals[1])
                            positions.append([float(val) for val in vals[2:5]])

                        self.data['atom_labels'] = np.asarray(symbols)
                        self.data['atom_positions'] = np.asarray(positions)

            # total_energy
            if self.data.get('energy_total') is None:
                m = re.search(self.restrs['energy_total'], line)
                if m:
                    self.data['energy_total'] = (
                        float(m.group('energy_total')) *
                        self.unit2ase[m.group('unit').lower()])

            if self.data.get('x_mopac_fhof') is None:
                m = re.search(self.restrs['x_mopac_fhof'], line)
                if m:
                    self.data['x_mopac_fhof'] = (
                        float(m.group('x_mopac_fhof')) *
                        self.unit2ase[m.group('unit').lower()])
            # forces
            if self.data.get('atom_forces') is None:
                m = re.search(self.restrs['forces_begin'], line)
                if m:
                    forces = []
                    for sline in self.lines[i + 3: i + 3 + natoms * 3]:
                        tmp = sline.split()
                        forces += [-float(tmp[6]) *
                                   self.unit2ase[tmp[7].lower()]]
                    forces = np.array(forces).reshape(natoms, 3)
                    self.data['atom_forces'] = forces

            # eigenvalues
            if self.data.get('n_filled') is None:
                m = re.search(self.restrs['n_filled'], line)
                if m:
                    self.data['n_filled'] = int(m.group('n_filled'))

            if self.data.get('n_alpha') is None:
                m = re.search(self.restrs['n_alpha'], line)
                if m:
                    self.data['n_alpha'] = int(m.group('n_alpha'))

            if self.data.get('n_beta') is None:
                m = re.search(self.restrs['n_beta'], line)
                if m:
                    self.data['n_beta'] = int(m.group('n_beta'))

            if self.data.get('eigenvalues_values') is None:
                m = re.search(self.restrs['eigenvalues_begin'], line)
                if m:
                    if 'ALPHA' in line:  # spin polarized calculation
                        eigs_a = self.rep2bl(i + 1, float)
                    elif 'BETA' in line:
                        eigs_b = self.rep2bl(i + 1, float)
                        eigs = np.array([eigs_a, eigs_b]).reshape(2, 1, -1)
                        self.data['eigenvalues_values'] = eigs
                    else:
                        eigs = np.array(self.rep2bl(i + 1,
                                                    float)).reshape(1, 1, -1)
                        self.data['eigenvalues_values'] = eigs

            if self.data.get('spin_S2') is None:
                m = re.search(self.restrs['spin_S2'], line)
                if m:
                    self.data['spin_S2'] = float(m.group('spin_S2'))

            if self.data.get('time_calculation') is None:
                m = re.search(self.restrs['time_calculation'], line)
                if m:
                    self.data['time_calculation'] = float(
                        m.group('time_calculation'))

        self.atoms = Atoms(self.data['atom_labels'],
                           positions=self.data['atom_positions'])

    def calculate_and_transform(self):
        # setup occupations, and homo, lumo, somo
        if self.data.get('total_charge') is None:
            self.data['total_charge'] = 0
        eigs = self.data.get('eigenvalues_values')
        if eigs is not None:
            occs = np.zeros(eigs.shape, float)
            nspin = eigs.shape[0]
            self.data['eigenvalues_kpoints'] = np.zeros((1, 3))  # Gamma only
            if nspin == 2:
                n_a = self.data.get('n_alpha')
                n_b = self.data.get('n_beta')
                self.data['number_of_electrons'] = np.array((n_a, n_b), float)
                occs[0, 0, :n_a] = 1.0
                occs[1, 0, :n_b] = 1.0
                self.data['energy_reference_highest_occupied'] = np.array(
                    (eigs[0, 0, n_a - 1], eigs[1, 0, n_b - 1]))
            else:
                n_f = self.data.get('n_filled')
                self.data['number_of_electrons'] = np.array((2 * n_f, ), float)
                occs[0, 0, :n_f] = 1.0
                self.data['energy_reference_highest_occupied'] = np.array(
                    (eigs[0, 0, n_f - 1],))

            self.data['eigenvalues_occupation'] = occs

        if self.data.get('inp_parm_line') is not None:
            inp_parm_line = self.data.get('inp_parm_line')
            if '1SCF' in inp_parm_line:
                structure_optimization = False
            else:
                structure_optimization = True
            self.data['x_mopac_optimization'] = structure_optimization

            for multiplicity, value in self.multiplicities.items():
                if multiplicity in [p.lower() for p in inp_parm_line.split()]:
                    self.data['spin_target_multiplicity'] = value
                    break

            for method in self.methods:
                if method in inp_parm_line:
                    self.data['x_mopac_method'] = method
                    break

    def __getattr__(self, name):
        return self.data.get(name)

    def __contains__(self, name):
        return name in self.data

if __name__ == '__main__':
    import sys
    fname = sys.argv[1]
    r = Reader(fname)
    print(r.eigenvalues_values.shape)
#    i = r.get_index(r"CALCULATION DONE:")
#    print('line number {0}| '.format(i) + r.lines[i])
    print('printing r.data')
    for key, val in r.data.items():
        if isinstance(val, np.ndarray):
            print(key, type(val), '| shape:', val.shape)
            if len(val.flat) <= 40:
                print(val)
        else:
            print(key, val)
