import sys
import re
from PyQt4 import QtGui, QtCore
import time
import serial
# import new_era
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import pdb

# TODO: 1. Repeated start button clicks only create one filewatcher instance
# TODO: 2. Stopping needs to kill the filewatcher (or at least incapacitate it)


serial_port = 'COM3'

syringes = {'1 ml BD': '4.699',
            '3 ml BD': '8.585',
            '10 ml BD': '14.60',
            '30ml BD': '21.59'}


# This class defines FileWatcher instances
# 1. Monitor files that end in file names defined by list 'patterns'
# 2.

class AddedFileWatcher(PatternMatchingEventHandler):
    def __init__(self, patterns, ignore_directories=True):
        super().__init__()
        self._ignore_directories = ignore_directories
        self._patterns = patterns

    def on_created(self, event):
        print('{} was added. Pumping X ul...'.format(event.src_path))
        pass  # Here: send signal instead of print and pass


class MenuTester(QtGui.QWidget):

    def __init__(self):
        super(MenuTester, self).__init__()
        self.obs = Observer()
        self.add_file_watcher = AddedFileWatcher(patterns=['*.txt'])
        self.initUI()

    def initUI(self):

        # set grid layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        # K directory indicator
        self.dir_status = 'Folder not set'
        self.dir_stat_bar = QtGui.QLabel(self)
        grid.addWidget(QtGui.QLabel(self.dir_stat_bar), 0, 0)
        self.dir_stat_bar.setText(self.dir_status)

        # K some labels
        # grid.addWidget(QtGui.QLabel(self.dir_status), 0, 0)
        grid.addWidget(QtGui.QLabel('Volume/image'), 0, 1)

        # K Row 2.1: Add button to select user directory where images from
        # microscope will be stored
        self.dirbutton = QtGui.QPushButton('Image Directory', self)
        grid.addWidget(self.dirbutton, 1, 0)
        # For linux testing
        self.image_dir = '/home/klas/PycharmProjects/pump_mod/AbateLab/test'
        # For windows testing
        # self.image_dir = 'C:\\Users\\admin'
        # self.image_dir = 'D:\\test_folder_programming\\add_files'
        self.dirbutton.clicked.connect(self.set_dir)

        # K Row 2.2: Add field to enter the volume pumped between images
        # initialize value
        self.vol_image = 0
        # Connect to a UI edit field
        self.vol_image = QtGui.QLineEdit(self)
        # Add widget to grid
        grid.addWidget(self.vol_image, 1, 1)

        # K Row 2.3: Add field to enter total volume of syringe?

        # K Row 3 Start Stop buttons
        self.runbtn = QtGui.QPushButton('Start Image Detection', self)
        grid.addWidget(self.runbtn, 2, 0)
        self.runbtn.setCheckable(True)
        self.runbtn.clicked.connect(self.detection_update)

        self.stopbtn = QtGui.QPushButton('Stop', self)
        grid.addWidget(self.stopbtn, 2, 1)
        self.stopbtn.setCheckable(True)
        # self.stopbtn.clicked.connect(self.stop_all)
        self.stopbtn.clicked.connect(self.fake_stop)
        
        # format the page, don't initialize anything below here
        self.setLayout(grid)
        self.setWindowTitle('Pump Control Testing')
        # self.setWindowFlags(self.windowFlags() |
        # QtCore.Qt.WindowStaysOnTopHint) # always on top
        self.show()

    def fake_stop(self):  # This button is used during testing
        if self.obs.is_alive():
            self.stopbtn.setChecked(1)
            self.runbtn.setChecked(0)
            # This should stop the instance of the file_added_watcher
            self.obs.stop()
            self.obs.join()
        else:
            self.stopbtn.setChecked(1)
            self.runbtn.setChecked(0)

    # K Adding function that gets user directory
    def set_dir(self):
        dialog = QtGui.QFileDialog()
        dir_path = dialog.getExistingDirectory(None, 'Select Folder')
        self.image_dir = dir_path
        self.dir_status = 'Folder Set!'
        # print('Dir is {}'.format(self.image_dir))
        # self.dir_status = re.split(r'[\\/]', dir_path)  # Should work
        self.dir_stat_bar.setText(self.dir_status)

    # K runs the continuous image detection until stopped
    def detection_update(self):
        if not self.obs.is_alive():
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)
            # pdb.set_trace()
            # Here insert call to method for setting up a file observer,
            # what would normally be in the main of a script
            self.obs.schedule(self.add_file_watcher, self.image_dir)
            self.obs.start()
        else:
            self.runbtn.setChecked(1)
            self.stopbtn.setChecked(0)

    # stopping program
    def shutdown(self):
        print('Stopped')


def main():  # Main; This might be better placed in the 'if__name__main'-
    # but keep it like this to conform with the source
    app = QtGui.QApplication(sys.argv)
    ex = MenuTester()
    ret = app.exec_()
    ex.shutdown()
    # print(ex.stop_indicator)
    sys.exit(ret)


if __name__ == '__main__':
    main()
