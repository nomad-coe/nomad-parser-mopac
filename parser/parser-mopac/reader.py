import numpy as np
from ase import Atoms
from ase import units
import re


class Reader:
    def __init__(self, filename):

        self.unit2ase = {  # convert to ase units (eV, Angstrom)
            'ev': units.eV,
            'kcal/mol': units.kcal / units.mol,
            'kj/mol': units.kJ / units.mol,
            'hartree': units.Hartree,
            'kcal/angstrom': units.kcal / units.mol / units.Angstrom,
        }
        # things to read
#        section_run = ['program_name', 'program_version']
#        section_system = ['atom_labels', 'atom_positions',
#                          'configuration_periodic_dimentions',
#                          'simulation_cell']
#        section_eigenvalues = ['eigenvalues_values',
#                               'eigenvalues_occupations']
#        section_single_configuration_calculation = ['energy_total',
#                                                    'atom_forces']
        with open(filename, 'r') as f:
            self.lines = f.readlines()

        self.data = {}
        self.restrs = {
            'program_version':
            re.compile(r"\s*Version\s*(?P<program_version>[0-9.a-zA-Z]+)\s+"),
            'natoms':
            re.compile(r"\s*Empirical\s*Formula:.*=\s*(?P<natoms>[1-9]+)"),
            'positions_begin':
            re.compile(r"\s*ATOM\s*CHEMICAL\s*X"),
            'energy_total':
            re.compile(r"\s*TOTAL\s*ENERGY\s*=\s*(?P<energy_total>[0-9.+-]+)\s*(?P<unit>[a-zA-Z]+)"),
            'forces_begin':
            re.compile(r"\s*FINAL\s*POINT\s*AND\s*DERIVATIVES"),
            'eigenvalues_begin':
            re.compile(r"\s*EIGENVALUES")}#        self.version =\
#        re.compile(r"\s*Version\s*(?P<program_version>[0-9.a-zA-Z]+)\s+")
        self.read()

    def read(self):
        # find number of atoms
        for line in self.lines:
            m = re.search(self.restrs['natoms'],
                          line)
            if m:
                self.data['natoms'] = natoms = int(m.group('natoms'))
                break

        for i, line in enumerate(self.lines):
            # program_version
            if self.data.get('program_version') is None:
                m = re.search(self.restrs['program_version'], line)
                if m:
                    self.data['program_version'] = m.group('program_version')
                    continue

            # atom_positions, atom_labels
            if self.data.get('atom_positions') is None:
                m = re.search(self.restrs['positions_begin'], line)
                if m:
                    symbols = []
                    positions = []
                    for sline in self.lines[i + 3: i + 3 + natoms]:
                        tmp = sline.split()
                        symbols.append(tmp[1])
                        positions.append([tmp[2], tmp[4], tmp[6]])
                    symbols = np.asarray(symbols)
                    self.data['atom_positions'] = np.array(positions, float)
                    self.data['atom_labels'] = np.array(symbols)
                    continue

            # total_energy 
            if self.data.get('energy_total') is None:
                m = re.search(self.restrs['energy_total'], line)
                if m:
                    self.data['energy_total'] = (float(m.group('energy_total')) *
                                                       self.unit2ase[m.group('unit').lower()])
                    continue

            # forces
            if self.data.get('atom_forces') is None:
                m = re.search(self.restrs['forces_begin'], line)
                if m:
                    atom_indices = []
                    forces = []
                    for sline in self.lines[i + 3: i + 3 + natoms * 3]:
                        tmp = sline.split()
                        atom_indices += [int(tmp[1])]
                        forces += [-float(tmp[6]) *
                                   self.unit2ase[tmp[7].lower()]]
                    forces = np.array(forces).reshape(natoms, 3)
                    self.data['atom_forces'] = forces
                    continue

            # eigenvalues
            if self.data.get('eigenvalues_values') is None:
                m = re.search(self.restrs['eigenvalues_begin'], line)
                if m:
                    if 'ALPHA' in line: # spin polarized calculation
                        eigs_alpha = np.array(self.lines[i+1].split(), float)
                        eigs_beta = np.array(self.lines[i+5].split(), float)
                        eigs = np.vstack([eigs_alpha,
                                          eigs_beta]).reshape(2,1,-1)
                        self.data['eigenvalues_values'] = eigs
                    else:
                        eigs = np.array(self.lines[i+1].split(), float).reshape(1, 1, -1)
                        self.data['eigenvalues_values'] = eigs
                    continue

        self.atoms = Atoms(self.data['atom_labels'],
                           positions=self.data['atom_positions'])


if __name__ == '__main__':
    import sys
    if len(sys.argv)==2:
        fname = sys.argv[1]
    else:
        fname = 'O2.out'

    r = Reader(fname)
    for key, val in r.data.items():
        print(key, val)
