"""
Reader for the Detector Responsivity System from Light Standards at MSL.
"""
import re
from datetime import datetime

import numpy as np

from msl.io import register, Reader


@register
class DRS(Reader):

    @staticmethod
    def can_read(url, **kwargs):
        """Checks if the first line starts with ``DRS`` and ends with ``Shindo``."""
        if Reader.get_extension(url).lower() != '.dat':
            return False
        line = Reader.get_lines(url, 1)[0]
        if line.startswith('DRS') and line.endswith('Shindo'):
            return True
        if line.startswith('"DRS') and line.endswith('Shindo"'):
            return True
        return False

    def read(self, **kwargs):
        """Reads the *.DAT* and corresponding *.LOG* file.

        Parameters
        ----------
        **kwargs
            All key-value pairs are ignored.
        """
        self._default_alias = {'l(nm)': 'wavelength'}

        self._lines_dat = self.get_lines(self.url, remove_empty_lines=True)
        self._num_lines_dat = len(self._lines_dat)

        self._lines_log = self.get_lines(self.url[:-3]+'LOG', remove_empty_lines=True)
        self._num_lines_log = len(self._lines_log)

        num_runs = 0
        self._index_dat = 0
        self._index_log = 0
        while self._index_dat < self._num_lines_dat:
            if 'DRS' in self._lines_dat[self._index_dat]:
                num_runs += 1
                group = self.create_group('run%d' % num_runs)
                self._read_run(group)
            else:
                self._index_dat += 1
                self._index_log += 1

    def _read_run(self, group):
        group.add_metadata(**self._get_run_metadata())

        # include all Scans
        scan_number = 0
        while self._index_dat < self._num_lines_dat and self._lines_dat[self._index_dat].startswith('Scan'):
            scan_number += 1
            sub = group.create_group('scan%d' % scan_number)
            self._get_scan_dat(sub)
            self._get_scan_log(sub)
            self._index_dat += 1
            self._index_log += 1

    def _get_run_metadata(self):
        # add the metadata from the LOG file

        assert 'DRS' in self._lines_log[self._index_log], self._lines_log[self._index_log]

        meta = dict()
        meta['version'] = re.search(r'version (\w+\s+\d{4})', self._lines_log[self._index_log]).group(1)
        meta['author'] = re.search(r'by\s(.*)', self._lines_log[self._index_log]).group(1)

        # skip lines until we reach the info about the wavelength scan values
        while not self._lines_log[self._index_log].startswith('Wavelength start'):
            self._index_log += 1

        # the info about the wavelength range
        assert self._lines_log[self._index_log].startswith('Wavelength start(nm)'), self._lines_log[self._index_log]
        meta['wavelength_units'] = 'nm'
        meta['wavelength_start'] = float(self._lines_log[self._index_log].split(':')[1])
        self._index_log += 1
        meta['wavelength_end'] = float(self._lines_log[self._index_log].split(':')[1])
        self._index_log += 1
        meta['wavelength_increment'] = float(self._lines_log[self._index_log].split(':')[1])
        self._index_log += 1
        if self._lines_log[self._index_log].startswith('Extra'):
            line_split = self._lines_log[self._index_log][len('Extra wavelength (nm):'):].split(';')
            extras = [val for val in line_split if val.strip()]
            meta['extra_wavelengths_nm'] = list(map(float, extras))
            self._index_log += 1

        # the info about the grating used and the bandwidth
        grating = re.search(r'at: (\d+) nm', self._lines_log[self._index_log])
        bw = re.search(r'correction: ([\d.]+) nm', self._lines_log[self._index_log])
        if grating and bw:
            meta['grating_nm'] = int(grating.group(1))
            meta['bandwidth_nm'] = float(bw.group(1))
        else:
            self._index_log -= 1  # go back a line

        # get the number of devices
        self._index_log += 1
        assert self._lines_log[self._index_log].startswith('Numbers of'), self._lines_log[self._index_log]
        # the info about the devices under test
        self._index_log += 1
        meta['devices'] = dict()
        self._names = [dev.strip().upper() for dev in self._lines_log[self._index_log].split('\t') if dev]
        if self._names[0].endswith('I'):
            skip = 1
            self._names = self._names[1:]
        else:
            skip = 0
        for name in self._names:
            meta['devices'][name] = dict()
        for label in ['Name', 'Tprobe', 'Channel']:
            self._index_log += 1
            line_split = [item.strip() for item in self._lines_log[self._index_log].split('\t') if item]
            device_key = label if skip == 0 else line_split[0]
            for index, name in enumerate(self._names):
                meta['devices'][name][device_key] = line_split[index + skip]

        # some LOG files have info about the lab temperature
        self._index_log += 1
        if self._lines_log[self._index_log].startswith('Laboratory Temperature'):
            line_split = [item.strip() for item in self._lines_log[self._index_log].split(';')]
            meta['Laboratory Temperature {}'.format(line_split[1])] = float(line_split[2])
            self._index_log += 1

        # some have info about the
        while 'R0=' in self._lines_log[self._index_log]:
            prt = self._lines_log[self._index_log].split('\t')
            prt_dict = {
                'R0': float(prt[1][3:]),
                'A': float(prt[3][2:]),
                'B': float(prt[5][2:]),
                'value': float(prt[7]),
            }
            meta[prt[0][:-1].strip()] = prt_dict
            self._index_log += 1

        if self._lines_log[self._index_log].startswith('Integration time'):
            meta['Integration time (s)'] = float(self._lines_log[self._index_log].split(':')[1])
            self._index_log += 1

        assert self._lines_log[self._index_log].startswith('Source Monitoring'), self._lines_log[self._index_log]
        meta['Source Monitoring'] = self._lines_log[self._index_log][len('Source Monitoring'):].strip()
        self._index_log += 1
        while 'DVM RANGE' in self._lines_log[self._index_log]:
            dvm = re.search(r'(\w+)::DVM RANGE\(V\)=\s+(.*\d+)\s+;\s+DVM NPLC=\s+(\d+)', self._lines_log[self._index_log])
            meta['{}_dvm_range'.format(dvm.group(1))] = float(dvm.group(2))
            meta['{}_dvm_nplc'.format(dvm.group(1))] = float(dvm.group(3))
            self._index_log += 1

        assert self._lines_log[self._index_log].startswith('Stray light filters'), self._lines_log[self._index_log]
        meta['Stray light filters'] = self._lines_log[self._index_log][len('Stray light filters'):].strip()

        # get the comment
        self._index_log += 1
        assert self._lines_log[self._index_log] == 'Comment:', self._lines_log[self._index_log]
        self._index_log += 1
        comment = []
        while not self._lines_log[self._index_log].startswith('Scan'):
            comment.append(self._lines_log[self._index_log])
            self._index_log += 1
        meta['comment'] = '\n'.join(comment)

        # move the DAT index to the start of the Scan
        while not self._lines_dat[self._index_dat].startswith('Scan'):
            self._index_dat += 1

        return meta

    def _get_scan_dat(self, group):
        meta = dict()

        assert self._lines_dat[self._index_dat].startswith('Scan'), self._lines_dat[self._index_dat]
        meta['start_time'] = self._to_datetime(self._lines_dat[self._index_dat])

        # get the field names to use for the numpy array
        aliases = self._default_alias.copy()
        for name in self._names:
            aliases[name] = group.parent.metadata.devices[name]['Name']

        self._index_dat += 1
        header = [item.strip() for item in self._lines_dat[self._index_dat].split('\t') if item]
        fieldnames = []
        for h in header:
            name = h
            for key, value in aliases.items():
                if key in h:
                    name = h.replace(key, value)
                    if name in fieldnames:
                        name += '-({})'.format(key[-1])
                    break
            fieldnames.append(name)

        # get the DAT data
        self._index_dat += 1
        data = []
        while self._index_dat < self._num_lines_dat and not self._lines_dat[self._index_dat].startswith('End'):
            data.append(tuple([float(item) for item in self._lines_dat[self._index_dat].split('\t') if item]))
            self._index_dat += 1

        if self._index_dat < self._num_lines_dat:  # otherwise the scan was aborted early
            assert self._lines_dat[self._index_dat].startswith('End of scan'), self._lines_dat[self._index_dat]
            meta['end_time'] = self._to_datetime(self._lines_dat[self._index_dat])

        # sometimes there was more data columns then header columns
        if data:
            i = 1
            while len(data[0]) > len(fieldnames):
                fieldnames.append('UNKNOWN-%d' % i)
                i += 1

        group.create_dataset(
            'dat',
            data=data,
            dtype=[(name, float) for name in fieldnames],
            **meta
        )

    def _get_scan_log(self, group):
        meta = dict()

        assert self._lines_log[self._index_log].startswith('Scan'), self._lines_log[self._index_log]
        meta['start_time'] = self._to_datetime(self._lines_log[self._index_log])

        # get the field names to use for the numpy array
        aliases = self._default_alias.copy()
        for name in self._names:
            aliases[name] = group.parent.metadata.devices[name]['Name']

        self._index_log += 1
        header = [item.strip() for item in self._lines_log[self._index_log].split('\t') if item.strip()]
        assert header[0] == 'l(nm)', self._lines_log[self._index_log]
        fieldnames = []
        for h in header:
            if h == 'Name':
                continue
            name = h
            for key, value in aliases.items():
                if key in h:
                    name = h.replace(key, value)
                    break
            if name not in fieldnames:
                fieldnames.append(name)

        # get the LOG data
        self._index_log += 1
        n = len(header)
        data = [[] for _ in self._names]
        while self._index_log < self._num_lines_log and not self._lines_log[self._index_log].startswith('End'):
            for i, name in enumerate(self._names):
                values = []
                items = [item for item in self._lines_log[self._index_log].split('\t') if item]
                for j, item in enumerate(items):
                    if j == 0:
                        values.append(float(item[:-2]))
                    elif j == 1:
                        assert item == aliases[name], 'expect Name={}, got {}'.format(aliases[name], item)
                    elif j >= n:
                        break
                    else:
                        values.append(float(item))

                # fill in the blank columns with NaN
                while len(values) < len(fieldnames):
                    values.append(np.NaN)

                data[i].append(tuple(values))
                self._index_log += 1

        if self._index_log < self._num_lines_log:  # otherwise the scan was aborted early
            assert self._lines_log[self._index_log].startswith('End of scan'), self._lines_log[self._index_log]
            meta['end_time'] = self._to_datetime(self._lines_log[self._index_log])

        for i, name in enumerate(self._names):
            vertex_name = 'log-' + aliases[name]
            vertex_name = vertex_name.replace('.', '')  # cannot contain a "."
            if vertex_name in group:
                vertex_name += '-({})'.format(name[-1])

            group.create_dataset(
                vertex_name,
                data=data[i],
                dtype=[(name, float) for name in fieldnames],
                **meta
            )

    def _to_datetime(self, line):
        string = line.split(',')[1].replace('p.m.', 'PM').replace('a.m.', 'AM').strip()
        try:
            return datetime.strptime(string, '%I:%M %p %d/%m/%Y')
        except ValueError:
            return datetime.strptime(string, '%d/%m/%Y %I:%M %p')
