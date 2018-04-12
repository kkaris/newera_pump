import os
import time
import sys
from PyQt4 import QtGui, QtCore
import serial
import new_era_vp as new_era
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import pdb

# ToDo | Nothing ToDo at the moment. Thu Apr 12 14:16:16 CDT 2018
# General comments:
# 1. Check what the maximum pump rate is and see if it might be reached by this
# program.
# 2. Left the prime functionality intact but commented. Maybe we want to save
# it for future use

global PAUSED
PAUSED = False

syringes = {'1 ml BD': '4.699',
            '3 ml BD': '8.585',
            '10 ml BD': '14.60',
            '30ml BD': '21.59'}

dt_sec = 0.5  # 0.5 seconds pump time from start to stop
dt_hr = dt_sec/3600.0


# Creates a class with a signal method
class FileCreateSignal(QtCore.QObject):

    create_signal = QtCore.pyqtSignal()


# This class defines AddedFileWatcher, a modified PatternMatchingEventHandler
# 1. Monitor files that end in file names defined by list 'patterns'
# 2. When a file matching the pattern is created, on_created is called and
# sends a signal.
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
        self.new_file_watch = AddedFileWatcher(patterns=['*.png', '*.gif',
                                                         '*.jpg', '*.tiff'])
        # Connect to pump_vol
        self.new_file_watch.fcs.create_signal.connect(self.pump_vol)
        self.initUI()
        
    def initUI(self):

        self.ser = serial.Serial(serial_port, 19200, timeout=.1)
        print('Connected to', self.ser.name)
        
        # set grid layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)
        
        # setup two buttons along top
        self.runbtn = QtGui.QPushButton('Start Image Detection', self)
        grid.addWidget(self.runbtn, 1, 2)
        self.runbtn.setCheckable(True)
        self.runbtn.setChecked(0)
        self.runbtn.clicked.connect(self.start_detection)

        self.stopbtn = QtGui.QPushButton('Stop', self)
        grid.addWidget(self.stopbtn, 1, 3)
        self.stopbtn.setCheckable(True)
        self.runbtn.setChecked(0)
        self.stopbtn.clicked.connect(self.stop_detection)

        # K Row 1.1: Add button to select user directory where images from
        # microscope will be stored
        self.dirbutton = QtGui.QPushButton('Image Directory', self)
        grid.addWidget(self.dirbutton, 1, 1)
        self.image_dir = ''
        # self.image_dir = 'C:\\Users\\admin'  # Standard?
        # Test this folder later: 'D:\\test_folder_programming\\add_files'
        self.dirbutton.clicked.connect(self.set_dir)

        # optional column labels
        grid.addWidget(QtGui.QLabel('Pump number'), 2, 0)
        grid.addWidget(QtGui.QLabel('Syringe'), 2, 1)
        grid.addWidget(QtGui.QLabel('Content'), 2, 2)
        grid.addWidget(QtGui.QLabel('Volume/pump (ul)'), 2, 3)
        grid.addWidget(QtGui.QLabel('Current vol (ul)'), 2, 4)
        
        # find pumps
        pumps = new_era.find_pumps(self.ser)
        
        # iterate over pumps, adding a row for each
        self.mapper = QtCore.QSignalMapper(self)
        # self.primemapper = QtCore.QSignalMapper(self)  # No priming
        self.currvol = dict()
        # self.currflow = dict()
        self.volumes = dict()
        self.rates = dict()
        # self.prime_btns = dict()  # No priming

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

            # add textbox to put syringe contents
            grid.addWidget(QtGui.QLineEdit(), row, 2)

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

        # set up the status bar
        self.curr_state = 'Running'
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
        self.run_update()
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
        dir_path = dialog.getExistingDirectory(None, 'Select microscope '
                                                     'image folder')
        self.image_dir = dir_path

    # K Start observer; How to handle start-stop-start? Observer can't be
    # restarted, so we need to replace the observer with a new one.
    def start_detection(self):
        global PAUSED
        PAUSED = False
        if self.image_dir == '':
            self.set_dir()

        if not self.obs.is_alive():
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)
            self.obs.schedule(self.new_file_watch, self.image_dir)
            self.obs.start()

        else:
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)

    # K Stop the observer, kill it?
    def stop_detection(self):
        global PAUSED
        PAUSED = True

        self.runbtn.setChecked(0)
        self.stopbtn.setChecked(1)
        self.stop_all()

    def stop_all(self):
        new_era.stop_all(self.ser)
        self.curr_state = 'Stopped'
        self.statusbar.setText('Status: '+self.curr_state)
        self.commandbar.setText('Last command: stop all pumps')
        [self.currvol[pump].setText('0 ul') for pump in self.rates]

        # No priming
        # self.prime_state = set()
        # [self.prime_btns[p].setChecked(0) for p in self.rates]

    def run_update(self):
        rates = {}
        # Get new rates from self.volumes and give to rates to send to pump(s)
        for pump in self.rates:

            # check if the flow rates are legit numbers (floats)
            if isfloat(self.volumes[pump].text().split()[0]):
                rate_phr = float(self.volumes[pump].text().split()[0]) / dt_hr
                self.rates[pump] = str(rate_phr) + ' ul/h'
                rates[pump] = str(self.rates[pump]).split()[0].strip()
                # pdb.set_trace()  # Check wth all rate_phr, rates[pump] are

            # else set to zero
            else:
                rates[pump] = '0.0'
                self.volumes[pump].setText('0.0')
                self.rates[pump] = '0.0 ul/h'

        if self.curr_state == 'Running':
            new_era.stop_all(self.ser)

        elif self.curr_state == 'Stopped':
            self.curr_state = 'Running'
            self.statusbar.setText('Status: ' + self.curr_state)

        # For both running and stop
        new_era.set_rates(self.ser, rates)
        new_era.run_all(self.ser)
        actual_rates = new_era.get_rates(self.ser, list(rates.keys()))
        self.commandbar.setText('Last command: update '+', '.join([
            'p%i=%s' % (p, actual_rates[p]) for p in actual_rates]))
        # Updated Volume = [rate (ul/hr)]*dt_hr
        rate_hr = float(actual_rates[pump]) * dt_hr
        [self.currvol[pump].setText(str(rate_hr) + ' ul')
         for pump in actual_rates]

    # K pump set volume by pumping the calculated rate for dt_sec seconds
    def pump_vol(self):
        # print('Reached pump_vol...')
        self.run_update()
        time.sleep(dt_sec)
        # time.sleep(2)  # For testing;
        self.stop_all()

    def update_syringe(self, pump):
        if self.curr_state == 'Stopped':
            dia = syringes[str(self.mapper.mapping(pump).currentText())]
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

        # Stop observer
        if self.obs.is_alive():
            self.obs.stop()
        try:  # Handles RuntimeError from exiting before starting the observer
            self.obs.join()
        except RuntimeError:
            pass

        # Close serial port connection
        self.ser.close()


def isfloat(n):
    try:
        float(n)
        return True
    except ValueError:
        return False


def main():
    app = QtGui.QApplication(sys.argv)
    ex = PumpControl()
    ret = app.exec_()
    ex.shutdown()
    sys.exit(ret)


if __name__ == '__main__':
    if sys.platform.lower() == 'linux':
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
        sys.exit(1)
