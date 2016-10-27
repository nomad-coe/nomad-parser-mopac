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

        with open(filename, 'r') as f:
            self.lines = f.readlines()

        self.data = {}
        self.restrs = {
            'program_version':
            re.compile(r"\s*Version\s*(?P<program_version>[0-9.a-zA-Z]+)\s+"),
            'natoms':
            re.compile(r"\s*Empirical\s*Formula:.*=\s*(?P<natoms>[0-9]+)"),
            'positions_begin':
            re.compile(r"\s*ATOM\s*CHEMICAL\s*X"),
            'energy_total':
            re.compile(r"\s*TOTAL\s*ENERGY\s*=\s*(?P<energy_total>[0-9.+-]+)\s*(?P<unit>[a-zA-Z]+)"),
            'forces_begin':
            re.compile(r"\s*FINAL\s*POINT\s*AND\s*DERIVATIVES"),
            'eigenvalues_begin':
            re.compile(r"\s*EIGENVALUES")}
        self.read()

    def _rep2bl(self, j, fun=float):
        """ Loop until a blank line is found, starting from line j.
            Parameters:
                j: starting line
                fun: [fun(x) for x in line.split()]
        """
        x = []
        while self.lines[j].rstrip():  # continue until a blank line
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
        for line in self.lines:
            m = re.search(self.restrs['natoms'],
                          line)
            if m:
                natoms = int(m.group('natoms'))
                break
        return natoms

    def read(self):
        natoms = self.get_natoms()
        self.data['natoms'] = natoms
        self.data['inp_parm_line'] = self.get_input_parameter_line()

        for i, line in enumerate(self.lines):
            # program_version
            if self.data.get('program_version') is None:
                m = re.search(self.restrs['program_version'], line)
                if m:
                    self.data['program_version'] = m.group('program_version')
                    #continue

            # atom_positions, atom_labels
            elif self.data.get('atom_positions') is None:
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
                    #continue

            # total_energy
            elif self.data.get('energy_total') is None:
                m = re.search(self.restrs['energy_total'], line)
                if m:
                    self.data['energy_total'] = (
                        float(m.group('energy_total')) *
                        self.unit2ase[m.group('unit').lower()])
                    #continue

            # forces
            elif self.data.get('atom_forces') is None:
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
                    #continue

            # eigenvalues
            elif self.data.get('eigenvalues_values') is None:
                m = re.search(self.restrs['eigenvalues_begin'], line)
                if m:
                    if 'ALPHA' in line:  # spin polarized calculation
                        eigs_a = self._rep2bl(i + 1, float)
                    elif 'BETA' in line:
                        eigs_b = self._rep2bl(i + 1, float)
                        eigs = np.array([eigs_a, eigs_b]).reshape(2, 1, -1)
                        self.data['eigenvalues_values'] = eigs
                    else:
                        eigs = np.array(self._rep2bl(i + 1,
                                                     float)).reshape(1, 1, -1)
                        self.data['eigenvalues_values'] = eigs
                    #continue

        self.atoms = Atoms(self.data['atom_labels'],
                           positions=self.data['atom_positions'])


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        fname = sys.argv[1]
    else:
        fname = 'O2.out'

    r = Reader(fname)
    i = r.get_index(r"CALCULATION DONE:")
    print('line number {0}| '.format(i) + r.lines[i])
    for key, val in r.data.items():
        print(key, val)
