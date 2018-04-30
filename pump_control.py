import sys
import time
from PyQt4 import QtGui, QtCore
import serial
import new_era_vp as new_era

# Syringe diameters
syringes = {'1 ml BD': '4.699',
            '3 ml BD': '8.585',
            '5 ml BD': '11.99',
            '10 ml BD': '14.43',
            '20 ml BD': '19.05',
            '30 ml BD': '21.59',
            '60 ml BD': '26.59'}

# Max rates translated from mL/hr to ul/hr (i.e. factor 10**3 increase)
max_rates = {'1 ml BD': 191100.0,
             '3 ml BD': 637900.0,
             '5 ml BD': 1244000.0,
             '10 ml BD': 1802000.0,
             '20 ml BD': 3141000.0,
             '30 ml BD': 4035000.0,
             '60 ml BD': 6120000.0}

# Min rates in ul/hr
min_rates = {'1 ml BD': 1.495,
             '3 ml BD': 4.868,
             '5 ml BD': 9.495,
             '10 ml BD': 13.76,
             '20 ml BD': 23.97,
             '30 ml BD': 30.79,
             '60 ml BD': 46.70}


class PumpControl(QtGui.QWidget):
    
    def __init__(self):
        super(PumpControl, self).__init__()
        self.initUI()
        
    def initUI(self):      

        self.ser = serial.Serial(serial_port, 19200, timeout=.1)
        print('connected to', self.ser.name)
        
        # set grid layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)
        
        # Run button
        self.runbtn = QtGui.QPushButton('Run/Update', self)
        grid.addWidget(self.runbtn, 1, 2)
        self.runbtn.setCheckable(True)
        self.runbtn.clicked.connect(self.run_update)

        # Stop button
        self.stopbtn = QtGui.QPushButton('Stop', self)
        grid.addWidget(self.stopbtn, 1, 3)
        self.stopbtn.setCheckable(True)
        self.stopbtn.clicked.connect(self.stop_all)

        # Optional column labels
        grid.addWidget(QtGui.QLabel('Pump number'), 2, 0)
        grid.addWidget(QtGui.QLabel('Syringe'), 2, 1)
        grid.addWidget(QtGui.QLabel('Content Label'), 2, 2)
        grid.addWidget(QtGui.QLabel('Flow rate'), 2, 3)
        grid.addWidget(QtGui.QLabel('Current flow rate'), 2, 4)
        
        # Find pumps
        pumps = new_era.find_pumps(self.ser)
        
        # Iterate over pumps, adding a row for each
        self.mapper = QtCore.QSignalMapper(self)
        self.primemapper = QtCore.QSignalMapper(self)
        self.currflow = dict()
        self.rates = dict()
        self.syr_max_rate = dict()
        self.syr_min_rate = dict()
        self.prime_btns = dict()
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

            self.syr_max_rate[pump] = 0.0  # max rate in ul/hr
            self.syr_min_rate[pump] = 0.0  # min rate in ul/hr

            # add textbox to put syringe contents
            grid.addWidget(QtGui.QLineEdit(), row, 2)

            # add textbox to enter flow rates
            self.rates[pump] = QtGui.QLineEdit(self)
            grid.addWidget(self.rates[pump], row, 3)

            # add label to show current flow rates
            self.currflow[pump] = QtGui.QLabel(self)
            self.currflow[pump].setAlignment(QtCore.Qt.AlignHCenter)
            grid.addWidget(self.currflow[pump], row, 4)

            # add prime button
            btn = QtGui.QPushButton('Prime', self)
            btn.setCheckable(True)  # makes the button toggleable
            self.primemapper.setMapping(btn, pump)
            btn.clicked.connect(self.primemapper.map)
            grid.addWidget(btn, row, 5)
            self.prime_btns[pump] = btn

        # mapper thing
        self.mapper.mapped.connect(self.update_syringe)        
        self.primemapper.mapped.connect(self.prime_pumps)        

        # set up the status bar
        self.curr_state = 'Running'
        self.statusbar = QtGui.QLabel(self)
        grid.addWidget(self.statusbar, 1, 4)
        self.statusbar.setText('Status: ' + self.curr_state)
        
        # set up the last command bar
        self.commandbar = QtGui.QLabel(self)
        grid.addWidget(self.commandbar, row + 1, 0, 1, 4)
        
        # make the prime state: a set containing the priming pumps
        self.prime_state = set()

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
        
    def stop_all(self):
        self.runbtn.setChecked(0)
        self.stopbtn.setChecked(1)
        new_era.stop_all(self.ser)
        self.curr_state = 'Stopped'
        self.statusbar.setText('Status: ' + self.curr_state)
        self.commandbar.setText('Last command: stop all pumps') 
        [self.currflow[pump].setText('0 ul/hr') for pump in self.rates]
        self.prime_state = set()
        [self.prime_btns[p].setChecked(0) for p in self.rates]

    def run_update(self):
        self.runbtn.setChecked(1)
        self.stopbtn.setChecked(0)

        # Update rates
        rates = {}
        for pump in self.rates:
            # check rates: isfloat(rate) && min_rate <= rate <= max_rate
            if isfloat(self.rates[pump].text()):
                if float(self.rates[pump].text()) <= self.syr_min_rate[pump]:
                    rates[pump] = self.syr_min_rate[pump]
                elif self.syr_max_rate[pump] <= float(self.rates[pump].text()):
                    rates[pump] = self.syr_max_rate[pump]
                else:
                    rates[pump] = str(self.rates[pump].text()).strip()
            else:
                rates[pump] = '0'
                self.rates[pump].setText('0')

        if self.curr_state == 'Running':
            new_era.stop_all(self.ser)
        elif self.curr_state == 'Stopped':
            self.curr_state = 'Running'
            self.statusbar.setText('Status: ' + self.curr_state)

        # Write rates to pump and run
        new_era.set_rates(self.ser, rates)
        new_era.run_all(self.ser)
        actual_rates = new_era.get_rates(self.ser, list(rates.keys()))
        self.commandbar.setText('Last command: run ' + ', '.join([
            'p%i=%s' % (p, actual_rates[p]) for p in actual_rates]))
        [self.currflow[pump].setText(actual_rates[pump] + ' ul/hr')
         for pump in actual_rates]
                 
    def update_syringe(self, pump):
        if self.curr_state == 'Stopped':
            dia = syringes[str(self.mapper.mapping(pump).currentText())]
            self.syr_max_rate[pump] = max_rates[str(self.mapper.mapping(
                pump).currentText())]
            self.syr_min_rate[pump] = min_rates[str(self.mapper.mapping(
                pump).currentText())]
            new_era.set_diameter(self.ser, pump, dia)
            dia = new_era.get_diameter(self.ser, pump)
            self.commandbar.setText('Last command: pump %i set to %s (%s '
                                    'mm)' % (pump, self.mapper.mapping(
                                     pump).currentText(), dia))
        else:
            self.commandbar.setText("Can't change syringe while running")

    def prime_pumps(self, pump):
        if self.curr_state == 'Stopped':
            if pump not in self.prime_state:  # currently not priming
                new_era.prime(self.ser, pump)
                self.commandbar.setText('Last command: priming pump %i' % pump)
                self.statusbar.setText('Status: Priming')
                self.prime_state.add(pump)  # add to prime state
            else:  # currently priming
                new_era.stop_pump(self.ser, pump)
                self.commandbar.setText('Last command: stopped pump %i' % pump)
                self.prime_state.remove(pump)  # remove prime state
                # if this is the last one, show status=Stopped
                if len(self.prime_state) == 0:
                    self.statusbar.setText('Status: Stopped')
            actual_rates = new_era.get_rates(self.ser, list(self.rates.keys()))
            self.currflow[pump].setText(actual_rates[pump] + ' ul/hr')
        else:
            self.commandbar.setText("Can't prime pump while running")
            self.prime_btns[pump].setChecked(0)

    def shutdown(self):
        self.stop_all()
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
        print('You missed to plug in the pump!')
        time.sleep(3)
        sys.exit(1)
