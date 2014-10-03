import sys
import sip
import serial
import time

from PyQt4.QtCore import pyqtSlot
from PyQt4.QtGui import *
from mainwindow import *
from Keithley import *


class ControlMainWindow(QtGui.QMainWindow):
    def __del__(self):
        self.keithleyPort.close()         
    
    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Config Slots
        self.ui.dcRadioButton.toggled.connect(self.switchSweepType)
        #self.ui.pulseRadioButton.toggled.connect(self.switchSweepType)
        
        # Measurement slots
        self.ui.measurementButton.clicked.connect(self.doSweep)
        self.ui.saveButton.clicked.connect(self.saveSweep)
        self.ui.clearDataButton.clicked.connect(self.clearSweep)
        
        # Port Magic
        self.keithleyPort = serial.Serial()
        self.keithleyPort.baudrate = 9600
        self.keithleyPort.port = "COM2"
        self.keithleyPort.timeout = 0.1
        self.keithley = Keithley()

        self.ui.keithleyPortOpenButton.clicked.connect(self.openKeithleyPort)
        self.ui.keithleyPortCloseButton.clicked.connect(self.closeKeithleyPort)

        self.fuckedUp = False
        self.data = []

    #
    # Config Slots
    #
    @pyqtSlot(bool)
    def switchSweepType(self, x):
        if x:
            self.ui.stackedWidget.setCurrentIndex(0)
        else:
            self.ui.stackedWidget.setCurrentIndex(1)
    #
    # Legacy Measurement slots
    #
    
    @pyqtSlot()
    def doSweep(self):
        #We're ready to sweep
        if self.keithley.port.isOpen():
            self.ui.progressBar.setRange(0, 0)
            
            #Legacy just in case
            if self.ui.legacySweepCheckbox.isChecked():
                self.doLegacySweep()
            #Full speed ahead =\
            else:            
                #DC Sweep
                self.fuckedUp = True
                if self.ui.dcRadioButton.isChecked():
                    if self.keithley.armDCMeasurements(remoteSensing=self.ui.fourWireRadio.isChecked(),
                                                       autorange=self.ui.autoRangeCheckBox.isChecked(),
                                                       range=self.ui.currentRangeSpinBox.value(),
                                                       limit=self.ui.currentLimitSpinBox.value()):
                        self.fuckedUp = False
                    else:
                        QMessageBox.error(self, "Error", "Couldn't arm DC Measurement")
                #Pulse Sweep
                else:
                    if self.keithley.armPulseMeasurements(remoteSensing=self.ui.fourWireRadio.isChecked(),
                                                          range=self.ui.currentRangeSpinBox.value(),
                                                          limit=self.ui.currentLimitSpinBox.value(),
                                                          pulseWidth=self.ui.pulseWidthSpinEdit.value()/1000.0,
                                                          pulseDelay=self.ui.pulseDelaySpinEdit.value()/1000.0):
                        self.fuckedUp = False
                    else:
                        QMessageBox.error(self, "Error", "Couldn't arm Pulse Measurement")
                    
                #Lets measure and read some points!
                if not self.fuckedUp:
                    #Linear Sweep
                    if self.ui.LinearRadioButton.isChecked():
                        start = self.ui.sweepStartVSpinEdit.value()
                        num = self.ui.NumPointsSpinBox.value()
                        step = (self.ui.sweepEndSpinEdit.value() - start)/(num - 1)
                        self.data = []
                        
                        for i in range(0, num):
                            #self.ui.progressBar.setValue(i/num)
                            app.processEvents()
                        
                            self.data.append(self.keithley.getPoint(voltage=(start + i*step),
                                                                    repeats=self.ui.numberOfSamplesSpinBox.value()))
                            print(str(i) + ": (" + str(self.data[i][0]) + ", " + str(self.data[i][1]) + ")")
                        QMessageBox.about(self, "Info", "Measurement complete!")
                    #Log Sweep
                    else:
                        QMessageBox.about(self, "Info", "Log sweep not yet implemented!")
        self.ui.progressBar.setRange(0, 1)

    @pyqtSlot()
    def doLegacySweep(self):
        if self.keithley.port.isOpen():
            
            self.keithley.doLegacySweep(startV=self.ui.sweepStartVSpinEdit.value(),
                                        endV=self.ui.sweepEndSpinEdit.value(),
                                        numberOfPoints=self.ui.NumPointsSpinBox.value(),
                                        remoteSensing=self.ui.fourWireRadio.isChecked(),
                                        logSteps=self.ui.LogRadioButton.isChecked(),
                                        autorange=self.ui.autoRangeCheckBox.isChecked(),
                                        range=self.ui.currentRangeSpinBox.value(),
                                        limit=self.ui.currentLimitSpinBox.value(),
                                        pulseSweep=self.ui.pulseRadioButton.isChecked(),
                                        pulseWidth=self.ui.pulseWidthSpinEdit.value()/1000.0,
                                        pulseDelay=self.ui.pulseDelaySpinEdit.value()/1000.0)

            QMessageBox.about(self, "Info", "Press Ok when measurement is complete")
            self.data = self.keithley.legacyReadDataPoints(self.ui.NumPointsSpinBox.value())
        else:
            QMessageBox.about(self, "Error", "Port Not Open")

    @pyqtSlot()
    def saveSweep(self):
        fname = QtGui.QFileDialog.getSaveFileName(self, caption="Save file", directory="e:\Documents\\",
                                                  filter="Text Files (*.txt *.dat *.csv)")
        f = open(fname, 'w')
        for point in self.data:
            f.write(str(point[0]) + ", " + str(point[1]) + "\n")
        f.close()
    
    @pyqtSlot()
    def clearSweep(self):
        self.data = []
        
    #
    # Port Magic
    #        

    @pyqtSlot()
    def openKeithleyPort(self):
        self.keithleyPort.port = self.ui.keithleyPortEdit.text()
        self.keithleyPort.close()
        print("Trying to open port... ", self.keithleyPort)
        self.keithleyPort.open()
        string = ""
        if self.keithleyPort.isOpen():
            self.keithleyPort.write(b"*IDN?\n")
            string = self.keithleyPort.read(128)
            string = str(string, "windows-1252")
            self.ui.keithleyPortLabel.setText(string)
            print(string)
        else:
            print("Failed to do something")
            self.ui.keithleyPortLabel.setText("Failed to read ID string")
            self.keithleyPport.close()
            
        if self.keithleyPort.isOpen():
            #Toggle ui
            self.ui.keithleyPortCloseButton.setEnabled(True)
            self.ui.measureTab.setEnabled(True)
            
            #Create Keithley class
            self.keithleyPort.close()
            self.keithley = Keithley.factory(string, self.keithleyPort)
            if not self.keithley.port.isOpen():
                self.keithley.port.open()
        
    @pyqtSlot()
    def closeKeithleyPort(self):
        #Close Keithley port
        self.keithley.port.close()
        self.ui.keithleyPortLabel.setText("Port Closed")
        
        #Toggle ui
        self.ui.keithleyPortCloseButton.setEnabled(False)
        self.ui.measureTab.setEnabled(False)
        
app = QtGui.QApplication(sys.argv)
mySW = ControlMainWindow()
mySW.show()
app.exec_()
#sys.exit(app.exec_())
