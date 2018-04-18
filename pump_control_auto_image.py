import os
import math
import time
import sys
from PyQt4 import QtGui, QtCore
import serial
import new_era_vp as new_era
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import pdb

# ToDo | 1. If there are two pumps, make sure that the second pump has the
# ToDo |    opposite pump direction as the first
# ToDo |
# ToDo | Issue: What happens if the pump hits the wall, i.e. if user puts in
# ToDo |    1 ml syringe that is pumped to 0.5 ml and enters 0.6 ml sample and
# ToDo |    screws the blocker to 0.5 ml?
# ToDo |
# ToDo | Future:
# ToDo |
# ToDo | General comments:
# ToDo | 1. Check what the maximum pump rate is and see if it might be reached
# ToDo |    by this program.
# ToDo | 2. Left the prime functionality commented but intact. Maybe we want
# ToDo |    to save it for future use
# ToDo |

global PAUSED, INF
PAUSED = True
INF = True

syringes = {'1 ml BD': '4.699',
            '3 ml BD': '8.585',
            '10 ml BD': '14.60',
            '30 ml BD': '21.59'}
syr_volumes = dict()
for key in syringes.keys():
    syr_volumes[key] = float(key.split()[0])*1000.0  # ml --> ul

dt_sec = 0.5  # 0.5 seconds pump time from start to stop
dt_hr = dt_sec/3600.0  # dt_sec in hours


# Creates a class with a signal method
class FileCreateSignal(QtCore.QObject):

    create_signal = QtCore.pyqtSignal()


# This class defines AddedFileWatcher, a modified PatternMatchingEventHandler
# 1. Monitor files that end in file names defined by list 'patterns'
# 2. When a file matching the pattern is created, on_created is called and
#    is set up to send a signal.
class AddedFileWatcher(PatternMatchingEventHandler):

    def __init__(self, patterns, ignore_directories=True):
        super().__init__()
        self._ignore_directories = ignore_directories
        self._patterns = patterns
        self.fcs = FileCreateSignal()

    def on_created(self, event):
        global PAUSED
        if PAUSED:
            pass
        elif not PAUSED:
            self.fcs.create_signal.emit()


class PumpControl(QtGui.QWidget):
    global PAUSED

    def __init__(self):
        super(PumpControl, self).__init__()

        # Create new instance of observer
        self.obs = Observer()

        # Create new instance of filewatcher
        self.new_file_watch = AddedFileWatcher(patterns=['*.png', '*.jpg'])
        # Connect to pump_vol
        self.new_file_watch.fcs.create_signal.connect(self.pump_vol)
        self.initUI()
        
    def initUI(self):

        self.ser = serial.Serial(serial_port, 19200, timeout=.1)
        print('Connected to', self.ser.name)
        
        # set grid layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        # Run Button
        self.runbtn = QtGui.QPushButton('Start Image Detection', self)
        grid.addWidget(self.runbtn, 1, 2)
        self.runbtn.setCheckable(True)
        self.runbtn.setChecked(0)
        self.runbtn.clicked.connect(self.start_detection)

        # Stop button
        self.stopbtn = QtGui.QPushButton('Stop', self)
        grid.addWidget(self.stopbtn, 1, 3)
        self.stopbtn.setCheckable(True)
        self.stopbtn.setChecked(0)
        self.stopbtn.clicked.connect(self.stop_detection)

        # K Row 1.1: Add button to select user directory where images from
        # microscope will be stored
        self.dirbutton = QtGui.QPushButton('Image Directory', self)
        grid.addWidget(self.dirbutton, 1, 1)
        self.image_dir = ''
        # self.image_dir = 'C:\\Users\\admin'  # Standard?
        # Test this folder later: 'D:\\test_folder_programming\\add_files'
        self.dirbutton.clicked.connect(self.set_dir)

        # Column labels
        grid.addWidget(QtGui.QLabel('Pump number'), 2, 0)
        grid.addWidget(QtGui.QLabel('Syringe'), 2, 1)
        grid.addWidget(QtGui.QLabel('Sample volume (ul)'), 2, 2)
        grid.addWidget(QtGui.QLabel('Volume/pump (ul)'), 2, 3)
        grid.addWidget(QtGui.QLabel('Current vol (ul)'), 2, 4)
        
        # find pumps
        pumps = new_era.find_pumps(self.ser)
        
        # iterate over pumps, adding a row for each
        self.mapper = QtCore.QSignalMapper(self)
        # self.primemapper = QtCore.QSignalMapper(self)  # No priming
        self.currvol = dict()
        # self.currflow = dict()
        self.sample_vol = dict()
        self.syr_volume = dict()
        self.volumes = dict()
        self.rates = dict()
        # self.prime_btns = dict()  # No priming

        # For future: only allow one or two pumps, no more. Second pump must
        # have same rate but with reversed direction to the first one
        for i, pump in enumerate(pumps):
            row = 3+i
            
            # add pump number
            pumplab = QtGui.QLabel('Pump %i' % pump)
            pumplab.setAlignment(QtCore.Qt.AlignHCenter)
            grid.addWidget(pumplab, row, 0)

            # add syringe pulldown
            combo = QtGui.QComboBox(self)
            [combo.addItem(s) for s in sorted(syringes)]
            self.mapper.setMapping(combo, pump)
            combo.activated.connect(self.mapper.map)
            grid.addWidget(combo, row, 1)

            # Syringe volume
            self.syr_volume[pump] = 0.0

            # Textbox to set sample volume
            self.sample_vol[pump] = QtGui.QLineEdit(self)
            self.sample_vol[pump].setText('0')
            grid.addWidget(self.sample_vol[pump], row, 2)

            # Textbox to add volume to pump
            self.volumes[pump] = QtGui.QLineEdit(self)
            self.volumes[pump].setText('0')
            grid.addWidget(self.volumes[pump], row, 3)
            # The unit for the rate is ul/hr while the user enters the volume
            # pumped per image in ul (and the pump is pumping for dt_sec sec)
            self.rates[pump] = str(
                int(self.volumes[pump].text().split()[0]) / dt_hr) + ' ul/h'

            # add label to show current volume pumped
            self.currvol[pump] = QtGui.QLabel(self)
            self.currvol[pump].setAlignment(QtCore.Qt.AlignHCenter)
            grid.addWidget(self.currvol[pump], row, 4)

            # No priming
            # No prime button! # add prime button
            # btn = QtGui.QPushButton('Prime', self)
            # btn.setCheckable(True)  # makes the button toggleable
            # self.primemapper.setMapping(btn, pump)
            # btn.clicked.connect(self.primemapper.map)
            # grid.addWidget(btn, row, 5)
            # self.prime_btns[pump] = btn

        # mapper thing
        self.mapper.mapped.connect(self.update_syringe)
        # No priming
        # self.primemapper.mapped.connect(self.prime_pumps)

        # Pump count status bar
        self.pump_counter = 0
        self.pump_count = QtGui.QLabel(self)
        grid.addWidget(self.pump_count, 0, 2)
        self.pump_count.setText('Pump count: {}'.format(self.pump_counter))

        # Volume infused
        self.pumped_volume = 0
        self.pump_volume = QtGui.QLabel(self)
        grid.addWidget(self.pump_volume, 0, 3)
        self.pump_volume.setText('Vol INF: {} (ul)'.format(self.pumped_volume))

        # set up the status bar
        self.curr_state = 'Stopped'+'; {}'.format('INF' if INF else 'WDR')
        self.statusbar = QtGui.QLabel(self)
        grid.addWidget(self.statusbar, 1, 4)
        self.statusbar.setText('Status: '+self.curr_state)

        # set up the last command bar
        self.commandbar = QtGui.QLabel(self)
        grid.addWidget(self.commandbar, row+1, 0, 1, 4)

        # No priming
        # make the prime state: a set containing the priming pumps
        # self.prime_state = set()

        # initialize: set all flow rates to zero
        self.run_update(self.rates)
        self.stop_all()
        [self.update_syringe(p) for p in pumps]
        self.commandbar.setText('')

        # keyboard shortcuts
        QtGui.QShortcut(QtGui.QKeySequence('Space'), self, self.stop_all)

        # format the page
        self.setLayout(grid)
        self.setWindowTitle('Pump control')
        # self.setWindowFlags(self.windowFlags() |
        # QtCore.Qt.WindowStaysOnTopHint) # always on top
        self.show()

    # K get user directory
    def set_dir(self):
        dialog = QtGui.QFileDialog()
        dir_path = dialog.getExistingDirectory(None, 'Select microscope image'
                                                     ' folder')
        self.image_dir = dir_path

    def update_rates(self):
        global INF, PAUSED

        # Just to be sure
        self.stop_all()

        # Calculate new rates from self.volumes and send to pump(s)
        rates = {}
        for pump in self.rates:
            # check if pump volumes and sample volumes are floats and > 0
            if is_positive_float(self.volumes[pump].text().split()[0]) \
                    and \
                    is_positive_float(self.sample_vol[pump].text().split()[0]):
                # Check if sample volume > syringe max volume; Must update
                # syringe volume before checking
                if float(self.sample_vol[pump].text().split()[0]) > \
                        self.syr_volume[pump]:
                    self.sample_vol[pump].setText('0.0')
                    print('Sample volume larger than syringe volume!')
                    self.runbtn.setChecked(0)
                    self.stopbtn.setChecked(0)
                    self.stop_all()
                    PAUSED = True
                # All good
                else:
                    rate_phr = float(self.volumes[pump].text().split()[0]) / \
                               dt_hr  # Translate volume to ul/hr
                    if INF:  # if infusing, rate_phr > 0
                        rate_phr = math.copysign(rate_phr, 1)
                    elif not INF:  # if withdrawing, rate_phr < 0
                        rate_phr = math.copysign(rate_phr, -1)
                    self.rates[pump] = str(rate_phr) + ' ul/h'
                    rates[pump] = str(self.rates[pump]).split()[0].strip()

            # else set to zero
            else:
                rates[pump] = '0.0'
                self.volumes[pump].setText('0.0')
                self.rates[pump] = '0.0 ul/h'
                # HERE CREATE POPUP
                print('Volumes > 0 required for both sample and pump per '
                      'image!')
                self.curr_state = 'Stopped' + '; {}'.format(
                    'INF' if INF else 'WDR')
                self.statusbar.setText('Status: ' + self.curr_state)
                self.runbtn.setChecked(0)
                self.stopbtn.setChecked(0)
                self.stop_all()
                PAUSED = True

        # Send new rates to the pump; Whichever the new rates are
        new_era.set_rates(self.ser, rates)

    # K Start observer
    def start_detection(self):
        global PAUSED, INF

        if self.image_dir == '':  # Checking if dir is set
            self.set_dir()

        self.update_rates()

        PAUSED = False

        if not self.obs.is_alive():
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)
            self.obs.schedule(self.new_file_watch, self.image_dir)
            self.obs.start()

        else:
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)

    # K Stop the observer by setting PAUSED to True
    def stop_detection(self):
        global PAUSED
        PAUSED = True

        self.runbtn.setChecked(0)
        self.stopbtn.setChecked(1)
        self.stop_all()
        [self.currvol[pump].setText('0 ul') for pump in self.rates]

    def stop_all(self):
        new_era.stop_all(self.ser)
        self.curr_state = 'Stopped'+'; {}'.format('INF' if INF else 'WDR')
        self.statusbar.setText('Status: '+self.curr_state)
        self.commandbar.setText('Last command: stop all pumps')

        # No priming
        # self.prime_state = set()
        # [self.prime_btns[p].setChecked(0) for p in self.rates]

    def run_update(self, rates):
        global PAUSED, INF

        if self.curr_state[:7] == 'Running':
            new_era.stop_all(self.ser)

        elif self.curr_state[:7] == 'Stopped':

            self.curr_state = 'Running'+'; {}'.format('INF' if INF else 'WDR')
            self.statusbar.setText('Status: ' + self.curr_state)

        # For both running and stop
        new_era.run_all(self.ser)
        actual_rates = new_era.get_rates(self.ser, list(rates.keys()))
        self.commandbar.setText('Last command: update '+', '.join([
            'p%i=%s' % (p, actual_rates[p]) for p in actual_rates]))
        # Update volume = rate*dt_hr
        rate_hr = float(actual_rates[0]) * dt_hr
        [self.currvol[pump].setText(str(rate_hr) + ' ul')
         for pump in actual_rates]

    # K pump set volume by pumping the calculated rate for dt_sec seconds
    def pump_vol(self):
        global INF

        # pumping
        self.run_update(self.rates)
        time.sleep(dt_sec)
        # time.sleep(2)  # For testing;
        self.stop_all()

        # Increase counter by 1
        self.pump_counter += 1
        self.pump_count.setText('Tot pump: {}'.format(self.pump_counter))

        # Add current volume being pumped on pump 0 to total pump
        pumped = float(self.currvol[0].text().split()[0])
        self.pumped_volume += pumped
        self.pump_volume.setText('Vol INF: {} (ul)'.format(self.pumped_volume))

        # change directions if volume of syringe/sample is reached next
        # pump iteration or if next iteration withdraws more than original
        # sample volume
        if self.pumped_volume + pumped > \
                min(self.syr_volume[0], float(self.sample_vol[0].text())) \
                or self.pumped_volume + pumped < 0:
            INF = not INF  # Change direction to opposite of current
            self.update_rates()  # Update the rates

    def update_syringe(self, pump):
        if self.curr_state[:7] == 'Stopped':
            dia = syringes[str(self.mapper.mapping(pump).currentText())]
            self.syr_volume[pump] = syr_volumes[str(self.mapper.mapping(
                pump).currentText())]
            new_era.set_diameter(self.ser, pump, dia)
            dia = new_era.get_diameter(self.ser, pump)
            self.commandbar.setText('Last command: pump %i set to %s (%s '
                                    'mm)' % (pump, self.mapper.mapping(
                                     pump).currentText(), dia))
        else:
            self.commandbar.setText('Can\'t change syringe while running!')

    # No priming
    # def prime_pumps(self, pump):
    #     if self.curr_state == 'Stopped':
    #         if pump not in self.prime_state:  # currently not priming
    #             new_era.prime(self.ser, pump)
    #             self.commandbar.setText('Last command: priming pump %i'%pump)
    #             self.statusbar.setText('Status: Priming')
    #             self.prime_state.add(pump)  # add to prime state
    #
    #         else:  # currently priming
    #             new_era.stop_pump(self.ser, pump)
    #             self.commandbar.setText('Last command: stopped pump %i'%pump)
    #             self.prime_state.remove(pump)  # remove prime state
    #
    #             # if this is the last one, show status=Stopped
    #             if len(self.prime_state) == 0:
    #                 self.statusbar.setText('Status: Stopped')
    #         actual_rates = new_era.get_rates(self.ser,list(self.rates.keys()))
    #
    #         rate_hr = float(actual_rates[pump]) * dt_hr
    #         self.currvol[pump].setText(str(rate_hr) + ' ul')
    #     else:
    #         self.commandbar.setText('Can\'t prime pump while running')
    #         self.prime_btns[pump].setChecked(0)

    def shutdown(self):

        # Stop all pumps
        self.stop_all()

        # With hopes that this will solve the pumping of previously run rates
        # at startup
        rates = {}
        for pump in self.rates:
            rates[pump] = '0.0'
        new_era.set_rates(self.ser, rates)

        # Stop observer
        if self.obs.is_alive():
            self.obs.stop()
        try:  # Handles RuntimeError from exiting before starting the observer
            self.obs.join()
        except RuntimeError:
            pass
        finally:
            # Close serial port connection
            self.ser.close()


def sign(x): return math.copysign(1, x)


def isfloat(n):
    try:
        float(n)
        return True
    except ValueError:
        return False


def is_positive_float(n):
    if isfloat(n):
        if float(n) > 0:
            return True
        else:
            return False
    else:
        return False


def main():
    app = QtGui.QApplication(sys.argv)
    ex = PumpControl()
    ret = app.exec_()
    ex.shutdown()
    sys.exit(ret)


if __name__ == '__main__':
    if sys.platform.lower() == 'linux':  # Try Linux first
        serial_port = '/dev/ttyUSB0'
    else:  # We're probably on windows
        serial_port = 'COM3'

    try:
        ser = serial.Serial(serial_port, 19200, timeout=.1)
        ser.close()
        main()
    except serial.serialutil.SerialException:
        print('Failed to connect to {} / {}'.format(serial_port, sys.platform))
        print('I am afraid I cannot start the program without a serial port '
              'to connect to.')
        time.sleep(2)
        sys.exit(1)
