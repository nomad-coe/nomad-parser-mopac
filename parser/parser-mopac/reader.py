import numpy as np
from ase import Atoms
from ase import units
import re


class Reader:
    methods = ['AM1', 'MNDO', 'MNDOD', 'PM3', 'PM6', 'PM6-D3', 'PM6-DH+',
               'PM6-DH2', 'PM6-DH2X', 'PM6-D3H4', 'PM6-D3H4X', 'PMEP', 'PM7',
               'PM7-TS', 'RM1']

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
            re.compile(r"NO.\s*OF\s*BETA\s*ELECTRONS\s*=\s*(?P<n_beta>[0-9]+)")
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
            x.append([fun(e) for e in self.lines[j].split()])
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

        self.atoms = Atoms(self.data['atom_labels'],
                           positions=self.data['atom_positions'])

    def calculate_and_transform(self):
        #setup occupations, and homo, lumo, somo
        eigs = self.data.get('eigenvalues_values')
        if eigs is not None:
            occs = np.zeros(eigs.shape, float)
            nspin = eigs.shape[0]
            if nspin == 2:
                n_a = self.data.get('n_alpha')
                n_b = self.data.get('n_beta')
                occs[0, 0, :n_a] = 1.0
                occs[1, 0, :n_b] = 1.0
            else:
                n_f = self.data.get('n_filled')
                occs[0, 0, :n_f] = 1.0

            self.data['eigenvalues_occupation'] = occs

        if self.data.get('inp_parm_line') is not None:
            inp_parm_line = self.data.get('inp_parm_line')
            if '1SCF' in inp_parm_line:
                structure_optimization = False
            else:
                structure_optimization = True

            self.data['x_mopac_optimization'] = structure_optimization

            for method in self.methods:
                if method in inp_parm_line:
                    self.data['x_mopac_method'] = method
                    break

if __name__ == '__main__':
    import sys
    fname = sys.argv[1]

    r = Reader(fname)
#    i = r.get_index(r"CALCULATION DONE:")
#    print('line number {0}| '.format(i) + r.lines[i])
    print('printing r.data')
    for key, val in r.data.items():
        print(key, val)
