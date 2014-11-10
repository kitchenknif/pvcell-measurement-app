import sys
import sip
import serial
import time
                                                                                                                        #
from PyQt4.QtCore import pyqtSlot                                                                                       #
from PyQt4.QtGui import *                                                                                               # Системные библиотеки
from mainwindow import *                                                                                                # Библиотека графического интерфейса
from Keithley import *                                                                                                  # Библиотека общения с приборами Keithley


class ControlMainWindow(QtGui.QMainWindow):                                                                             # Класс главного окна
    def __del__(self):                                                                                                  # Уничтожение класса, на всякий случай закрываем порт, чтоб он не повис
        self.keithleyPort.close()         
    
    def __init__(self, parent=None):                                                                                    # Создаём класс (главное окно)
        super(ControlMainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()                                                                                       # Загружаем информацию о расположениее кнопочек - mainwindow.py, файл создаётся
                                                                                                                        # "автоматически" после редактирования интерфейса внешней программой qtDesigner
        self.ui.setupUi(self)

        # Config Slots                                                                                                  # Подключаем функции пограммы к кнопкам интерфейса
        self.ui.dcRadioButton.toggled.connect(self.switchSweepType)
        #self.ui.pulseRadioButton.toggled.connect(self.switchSweepType)
        #self.filePath = os.getcwd()
        self.filePath = "e:\Documents\\"
        
        # Measurement slots
        self.ui.measurementButton.clicked.connect(self.doSweep)
        self.ui.saveButton.clicked.connect(self.saveSweep)
        self.ui.clearDataButton.clicked.connect(self.clearSweep)
        
        # Port Magic                                                                                                    # Задаём дефолтные настройки порта
        self.keithleyPort = serial.Serial()
        self.keithleyPort.baudrate = 9600
        self.keithleyPort.port = "COM2"
        self.keithleyPort.timeout = 0.1
        self.keithley = Keithley()

        self.ui.keithleyPortOpenButton.clicked.connect(self.openKeithleyPort)                                           # Подключаем функции пограммы к кнопкам интерфейса
        self.ui.keithleyPortCloseButton.clicked.connect(self.closeKeithleyPort)

        self.fuckedUp = False                                                                                           # Пара внутренних переменных для работы с данными
        self.data = []

    #
    # Config Slots
    #
    @pyqtSlot(bool)
    def switchSweepType(self, x):                                                                                       # Вроде выбираем между импульсным режимиом или режимом постоянного тока
        if x:                                                                                                           # Панелька в низу интерфейса меняется когда выбирашь другой режим
            self.ui.stackedWidget.setCurrentIndex(0)
        else:
            self.ui.stackedWidget.setCurrentIndex(1)

    @pyqtSlot()
    def doSweep(self):                                                                                                  # Измеряй, сохраняй властвуй!
        #We're ready to sweep
        if self.keithley.port.isOpen():                                                                                 #Бесполезные сторчки
            self.ui.progressBar.setRange(0, 0)
            
            #Legacy just in case
            if self.ui.legacySweepCheckbox.isChecked() or self.keithley.type == '2635A':                                # Если запрашиваем "старый режим работы" или же у нас прибор 2635А,
                self.doLegacySweep()                                                                                    # Измеряем по старинке.
            #Full speed ahead =\
            else:                                                                                                       # Нет? Страдаем новыми приблудами.
                #DC Sweep
                self.fuckedUp = True                                                                                    # Априори считаем, что всё сломалось пока не узнали обратное
                if self.ui.dcRadioButton.isChecked():                                                                   # Если работаем в режиме постоянного тока, пытаемся настроить прибор для работы в этом режиме
                    if self.keithley.armDCMeasurements(remoteSensing=self.ui.fourWireRadio.isChecked(),                 # Задаем 2х или 4х проводную схему
                                                       autorange=self.ui.autoRangeCheckBox.isChecked(),                 # Включаем или выключаем режим автопобора диапаозона
                                                       range=self.ui.currentRangeSpinBox.value(),                       # Если выключен автопобор, работаем в этом диапазоне
                                                       limit=self.ui.currentLimitSpinBox.value()):                      # Макисмальный ток который можно пропускать через образец
                        self.fuckedUp = False                                                                           # Мы смогли всё хорошо
                    else:
                        QMessageBox.error(self, "Error", "Couldn't arm DC Measurement")                                 # Не смогли, ругаемся
                #Pulse Sweep
                else:                                                                                                   # Нет, хотим импульсный
                    if self.keithley.armPulseMeasurements(remoteSensing=self.ui.fourWireRadio.isChecked(),              # 4х проводная?
                                                          range=self.ui.currentRangeSpinBox.value(),                    # диапазон измерений?
                                                          limit=self.ui.currentLimitSpinBox.value(),                    # ограничение по току?
                                                          pulseWidth=self.ui.pulseWidthSpinEdit.value()/1000.0,         # ширина импульса
                                                          pulseDelay=self.ui.pulseDelaySpinEdit.value()/1000.0):        # задержка между импульсами
                        self.fuckedUp = False                                                                           # получилось
                    else:
                        QMessageBox.error(self, "Error", "Couldn't arm Pulse Measurement")                              # не получилось
                    
                #Lets measure and read some points!
                if not self.fuckedUp:                                                                                   # ух ты, смогли, давайте данные получать!
                    #Linear Sweep
                    if self.ui.LinearRadioButton.isChecked():                                                           # линейный шаг?
                        start = self.ui.sweepStartVSpinEdit.value()                                                     # начальное напряжение
                        num = self.ui.NumPointsSpinBox.value()                                                          # сколько точек?
                        step = (self.ui.sweepEndSpinEdit.value() - start)/(num - 1)                                     # шаг по напряжению
                        self.data = []                                                                                  # обнуляем данные
                        
                        for i in range(0, num):                                                                         # для каждой точки
                            #self.ui.progressBar.setValue(i/num)
                            app.processEvents()                                                                         # не вешаем интерфейс
                        
                            self.data.append(self.keithley.getPoint(voltage=(start + i*step),
                                                                    repeats=self.ui.numberOfSamplesSpinBox.value()))    # Получаем ток при заданном напряжении, усреднённый по N измерениям
                            print(str(i) + ": (" + str(self.data[i][0]) + ", " + str(self.data[i][1]) + ")")            # Выводим в консоль
                        QMessageBox.about(self, "Info", "Measurement complete!")                                        # ух ты получилось
                    #Log Sweep
                    else:
                        QMessageBox.about(self, "Info", "Log sweep not yet implemented!")                               # А логарифмическую шкалу пока не сделал, всё равно не использовали ни разу...
        self.ui.progressBar.setRange(0, 1)

    @pyqtSlot()
    def doLegacySweep(self):                                                                                            # Если вдруг захотелось получить данные по старинке
        if self.keithley.port.isOpen():
            
            self.keithley.doLegacySweep(startV=self.ui.sweepStartVSpinEdit.value(),                                     # начальное напряжение?
                                        endV=self.ui.sweepEndSpinEdit.value(),                                          # конечное напряжение?
                                        numberOfPoints=self.ui.NumPointsSpinBox.value(),                                # сколько точек?
                                        remoteSensing=self.ui.fourWireRadio.isChecked(),                                # 4х проводная схема?
                                        logSteps=self.ui.LogRadioButton.isChecked(),                                    # логарифмические шаги
                                        autorange=self.ui.autoRangeCheckBox.isChecked(),                                # автодиапазон
                                        range=self.ui.currentRangeSpinBox.value(),                                      # диапазон токов // по измерениям // точность измерения
                                        limit=self.ui.currentLimitSpinBox.value(),                                      # ограничение тока
                                        pulseSweep=self.ui.pulseRadioButton.isChecked(),                                # импульсный режим?
                                        pulseWidth=self.ui.pulseWidthSpinEdit.value()/1000.0,                           # ширина импульса
                                        pulseDelay=self.ui.pulseDelaySpinEdit.value()/1000.0)                           # задержка между импульсами

            QMessageBox.about(self, "Info", "Press Ok when measurement is complete")
            self.data = self.keithley.legacyReadDataPoints(self.ui.NumPointsSpinBox.value())                            # Читаем  данные по старинке
        else:
            QMessageBox.about(self, "Error", "Port Not Open")

    @pyqtSlot()
    def saveSweep(self):                                                                                                # Сохраняем данные с файл
        fname = QtGui.QFileDialog.getSaveFileName(self, caption="Save file", directory=self.filePath,                   # Получаем имя файла
                                                  filter="Text Files (*.txt *.dat *.csv)")
        self.filePath = os.path.dirname(fname)
        f = open(fname, 'w')
        for point in self.data:                                                                                         # Пишем точки. "Напряжение, Ток"
            f.write(str(point[0]) + ", " + str(point[1]) + "\n")
        f.close()
    
    @pyqtSlot()
    def clearSweep(self):                                                                                               # Ощичаем внутренее хранилище данных
        self.data = []
        
    #
    # Port Magic
    #        

    @pyqtSlot()
    def openKeithleyPort(self):                                                                                         # Открываем порт
        self.keithleyPort.port = self.ui.keithleyPortEdit.text()                                                        # Название порта берём из текстового поля
        self.keithleyPort.close()                                                                                       # Закрываем, если вдруг открыт - не хотим всё повесить
        print("Trying to open port... ", self.keithleyPort)
        self.keithleyPort.open()                                                                                        # А теперь открываем!
        string = ""
        if self.keithleyPort.isOpen():                                                                                  # Если получаилось,
            self.keithleyPort.write(b"*IDN?\n")                                                                         ## Пишем в прибор запрос на идентификатор
            string = self.keithleyPort.read(128)                                                                        ## Читаем идентификатор
            string = str(string, "windows-1252")                                                                        ## Читаем с правильной кодировкой
            self.ui.keithleyPortLabel.setText(string)                                                                   ## Пишем в интерфейс идентификатор
            print(string)                                                                                               ## и в консоль тоже пришем
        else:                                                                                                           # Не получилось,
            print("Failed to do something")                                                                             ## Ноем в консоль
            self.ui.keithleyPortLabel.setText("Failed to read ID string")                                               ## Ноем в интерфейс
            self.keithleyPport.close()                                                                                  ## Закрываем
            
        if self.keithleyPort.isOpen():                                                                                  # Вроде пока всё получается,
            #Toggle ui
            self.ui.keithleyPortCloseButton.setEnabled(True)                                                            ## Подрубаем интерфейс разговаривающий с прибором
            self.ui.measureTab.setEnabled(True)
            
            #Create Keithley class
            self.keithleyPort.close()                                                                                   ## Зачем-то закрываем порта
            self.keithley = Keithley.factory(string, self.keithleyPort)                                                 ## Создаём объект прибора
            if not self.keithley.port.isOpen():                                                                         ## Если чё, опять открываем порт.
                self.keithley.port.open()
        
    @pyqtSlot()
    def closeKeithleyPort(self):                                                                                        # Закрываем порт
        #Close Keithley port
        self.keithley.port.close()                                                                                      # Закрыли порт
        self.ui.keithleyPortLabel.setText("Port Closed")
        
        #Toggle ui
        self.ui.keithleyPortCloseButton.setEnabled(False)                                                               # Отключили элементы интерфейса, работающие с прибором
        self.ui.measureTab.setEnabled(False)
        
app = QtGui.QApplication(sys.argv)                                                                                      # Создаём окно и запускаем программу
mySW = ControlMainWindow()
mySW.show()
app.exec_()
#sys.exit(app.exec_())
