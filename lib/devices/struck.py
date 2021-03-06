#!/usr/bin/env python
import sys
import time
import copy
import numpy
import epics
import epics.devices

class Struck(epics.Device):
    """
    Very simple implementation of Struck SIS MultiChannelScaler
    """
    attrs = ('ChannelAdvance', 'Prescale', 'EraseStart',
             'EraseAll', 'StartAll', 'StopAll',
             'PresetReal', 'ElapsedReal',
             'Dwell', 'Acquiring', 'NuseAll',
             'CurrentChannel', 'InitialChannelAdvance',
             'SoftwareChannelAdvance', 'Channel1Source',
             'ReadAll', 'DoReadAll', 'Model', 'Firmware')

    _nonpvs  = ('_prefix', '_pvs', '_delim', '_nchan',
               'clockrate', 'scaler', 'mcas')

    def __init__(self, prefix, scaler=None, nchan=8, clockrate=50.0):
        if not prefix.endswith(':'):
            prefix = "%s:" % prefix
        self._nchan = nchan
        self.scaler = None
        self.clockrate = clockrate # clock rate in MHz

        if scaler is not None:
            self.scaler = epics.devices.Scaler(scaler, nchan=nchan)

        self.mcas = []
        for i in range(nchan):
            mcaname = "%smca%i" % (prefix,i+1)
            self.mcas.append(epics.devices.Mca(mcaname))
            
        epics.Device.__init__(self, prefix, delim='',
                              attrs=self.attrs, mutable=False)

    def ExternalMode(self, initialadvance=0, realtime=0, prescale=1):
        """put Struck in External Mode, with the following options:
        option            meaning                   default value
        ----------------------------------------------------------
        initialadvance  set Initial Channel Advance    0
        reatime         set Preset Real Time           0
        prescale        set Prescale value             1
        """
        out = self.put('ChannelAdvance', 1)  # external
        if self.scaler is not None:
            self.scaler.OneShotMode()
        if realtime is not None:
            self.put('PresetReal', realtime)
        if prescale is not None:
            self.put('Prescale', prescale)
        if initialadvance is not None:
            self.put('InitialChannelAdvancel', initialadvance)

        return out

    def InternalMode(self, prescale=None):
        "put Struck in Internal Mode"
        out = self.put('ChannelAdvance', 0)  # internal
        if self.scaler is not None:
            self.scaler.OneShotMode()
        if prescale is not None:
            self.put('Prescale', prescale)
        return out

    def setPresetReal(self, val):
        "Set Preset Real Tiem"
        return self.put('PresetReal', val)

    def setDwell(self, val):
        "Set Dwell Time"
        return self.put('Dwell', val)

    def AutoCountMode(self):
        "set auto count mode"
        if self.scaler is not None:
            self.scaler.AutoCountMode()

    def start(self):
        "Start Struck"
        if self.scaler is not None:
            self.scaler.OneShotMode()
        return self.put('EraseStart', 1)

    def stop(self):
        "Stop Struck Collection"
        return self.put('StopAll', 1)

    def erase(self):
        "Start Struck"
        return self.put('EraseAll', 1)

    def mcaNread(self, nmca=1):
        "Read a Struck MCA"
        return self.get('mca%i.NORD' % nmca)

    def readmca(self, nmca=1, count=None):
        "Read a Struck MCA"
        return self.get('mca%i' % nmca, count=count)

    def saveMCAdata(self, fname='Struck.dat', mcas=None,
                    ignore_prefix=None, npts=None):
        "save MCA spectra to ASCII file"
        sdata = []
        names = []
        addrs = []
        if mcas is None:
            mcas = list(range(1, self._nchan+1))

        time.sleep(0.010)
        for nmca in mcas:
            if self.scaler is not None:
                scaler_name = self.scaler.get('NM%i' % nmca)
                if scaler_name is not None and len(scaler_name) > 0:
                    if (ignore_prefix is not None and
                        scaler_name.startswith(ignore_prefix)):
                        continue
                    sdata.append(self.readmca(nmca=nmca))
                    names.append(scaler_name.replace(' ', '_'))
                    addrs.append(self.scaler._prefix + 'S%i' % nmca)

            else:
                sdata.append(self.readmca(nmca=nmca))
                names.append(' MCA%i ' % nmca)

        try:
            sdata = numpy.array(sdata)
            sdata = sdata.transpose()
        except:
            sdata = numpy.zeros(self.nchan*2048)
            sdata.shape = (self.nchan, 2048)
            sdata[0,:] = 1.0
            sdata = sdata.transpose()

        # convert time to integer microseconds!
        sdata[:,0] = sdata[:,0]/self.clockrate

        nelem, nmca = sdata.shape
        if npts is None:
            npts = nelem
        npts = min(nelem, npts)
        fout = open(fname, 'w')
        fout.write('# Struck MCA data: %s \n' % self._prefix)
        fout.write('# Nchannels, Nmca = %i, %i\n' % (npts, nmca))
        fout.write('# Time in microseconds\n')
        fout.write('#----------------------\n')
        fout.write('# %s\n' % (' | '.join(addrs)))
        fout.write('# %s\n' % (' | '.join(names)))
        fmt   =  '%9i ' * nmca + '\n'
        [fout.write(fmt % tuple(sdata[i])) for i in range(npts)]
        fout.close()

if __name__ == '__main__':
    strk = Struck('13IDE:SIS1:')
    adv = 'ChannelAdvance'
    sys.stdout.write("%s = %s\n" % (adv, strk.PV(adv).char_value))
