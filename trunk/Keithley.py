import serial
import time
import os


class Keithley:                                                                                                         # Класс для приборов Keithley
    """Keithley Generic SourceMeter Class"""
        
    @staticmethod
    def factory(type, port):
        if "2430" in type:
            return Keithley_24XX(port, True)                                                                            # Создаём для 2430
        if "2400" in type:
            return Keithley_24XX(port, False)                                                                           # Создаём для 2400
        if "2635A" in type:
            return Keithley_2635a(port, True)                                                                           # Создаём для 2635А
        assert 0, "Bad identification string: " + type                                                                  # ЩИТО ВЫ МНЕ ПОДСУНУЛИ ИДИТЕ НАФИГ

#
# Keithley 24XX
#        
        
        
class Keithley_24XX(Keithley):                                                                                          # 2430 или 2400
    """Keithley 24XX I-V Measurement Class"""

    def __init__(self, port, supportPulse):                                                                             # Создаём. Если 2400 - отключаем имульсные режимы
        self.type = '24XX'
        self.port = port
        self.port.open()
        self.supportPulse = supportPulse
        self.DCArmed = False
        self.PulseArmed = False
    
    def __del__(self):                                                                                                  # При выключении закрываем порт.
        self.port.close()

    # Factory Sweep Thing
    def doLegacySweep(self, startV=0.0, endV=3.0, numberOfPoints=100, remoteSensing=True, logSteps=False,
                      autorange=True, range=1e-3, limit=1.0, pulseSweep=False, pulseWidth=1e-3, pulseDelay=1e0):        # ЗАПУСКАЙ СТАРЫЙ СПОСОБ СНЯТИЯ ДАННЫХ
        if self.port.closed:                                                                                            # Если порт закрыт - не смогли
            return False
        if not self.supportPulse and pulseSweep:                                                                        # Если импульсый пытаемся, но импусльный отключен - не смогли
            return False
            
        self.port.write(b"*RST;\n")                                                                                     # Скидываем на заодские настройки
        self.port.flushInput()                                                                                          # Очищаем буфер порта
        
        self.DCArmed = False                                                                                            # Не готовы измерять
        self.PulseArmed = False    
        
        if autorange and not pulseSweep:
            self.port.write(b":SOUR:SWE:RANG AUTO;\n")                                                                  # Автоматическая подбора диапазона
        else:
            s = ":SENS:CURR:RANGE " + str(range) + ";\n"                                                                # Ручная подборка диапазона
            self.port.write(s.encode('ascii'))
        
        if remoteSensing:
            self.port.write(b":SYST:RSEN ON;\n")                                                                        # 4х проводная
        else:
            self.port.write(b":SYST:RSEN OFF;\n")                                                                       # 2х проводная
       
        s = "" 
    
        if not pulseSweep:                                                                                              # Режим постоянного тока
            s += ":SENS:CURR:NPLC 10; :TRIG:COUN " + str(numberOfPoints) + "; "                                         # Про все эти параметры написано в мануале, стырил оттуда
            s += ":SOUR:FUNC VOLT; :SENS:FUNC \"CURR\"; :SENS:FUNC:CONC ON; :SENS:CURR:PROT " + str(limit) + "; "
            s += ":SOUR:VOLT:START " + str(startV) + "; :SOUR:VOLT:STOP " + str(endV) + "; "
            s += ":SOUR:VOLT:STEP " + str((endV - startV)/(numberOfPoints-1.0)) + "; :SOUR:VOLT:MODE SWE; "
            s += ":FORM:ELEM VOLT,CURR; "
            if logSteps:
                s += ":SOUR:SWE:SPAC LOG; "
            else:
                s += ":SOUR:SWE:SPAC LIN; "
            s += ":OUTP ON; :READ?; :SYST:BEEP 500,1;\n"
        else:                                                                                                           # Режим импульсного тока
            s += ":SOUR:FUNC:SHAP PULS; :SOUR:PULS:WIDT " + str(pulseWidth) + "; "
            s += ":SOUR:PULS:DEL " + str(pulseDelay) + "; " 
            s += ":SENS:CURR:NPLC 0.1; :TRIG:COUN " + str(numberOfPoints) + "; "
            s += ":SOUR:FUNC VOLT; :SENS:FUNC \"CURR\"; :SENS:FUNC:CONC ON; :SENS:CURR:PROT " + str(limit) + "; "
            s += ":SOUR:VOLT:START " + str(startV) + "; :SOUR:VOLT:STOP " + str(endV) + "; "
            s += ":SOUR:VOLT:STEP " + str((endV - startV)/(numberOfPoints-1.0)) + "; :SOUR:VOLT:MODE SWE; "
            s += ":FORM:ELEM VOLT,CURR; "
            if logSteps:                                                                                                # ЛОГАРИФМИЧНО
                s += ":SOUR:SWE:SPAC LOG; "
            else:
                s += ":SOUR:SWE:SPAC LIN; "                                                                             # НЕЛОГАРИФМИЧНО
            s += ":OUTP ON; :READ?; :SYST:BEEP 500,1;\n"                                                                # Запустили, потом слили все данные на комп, потом издали истошный звук

        self.port.write(s.encode('ascii'))                                                                              # Отправили все эти команды на прибор

        return True
    
    def legacyReadDataPoints(self, numberOfPoints):                                                                     # Читаем по старинке
        dataPoints = []
        self.port.write(b":OUTP OFF;\n")                                                                                # Пора вырубить напряжение прибора
        p = self.port.readline()                                                                                        # Читаем строчку
        
        t = p.split(b",")                                                                                               # Разделяем строчку по запятой
        for i in range(0, len(t), 2):                                                                                   # Nточек раз пытаемся прочитать строчку, разделить по запятой и записать данные в виде чисел в массив dataPoints
            try:
                dataPoints.append([float(t[i]), float(t[i+1])])
            except ValueError:
                pass
        return dataPoints                                                                                               # Возвращаем массив датаПойнтся
        
    #
    # Realtime DC Sweep
    #
    
    def armDCMeasurements(self, remoteSensing=True, autorange=True, range=1e-3, limit=1.0):                             # Готовим моднявые измерения, Постояный ток
        if self.port.closed:                                                                                            # Если порт не открыт, валим боком. нам здесь не рады
            return False

        self.port.write(b"*RST;\n")                                                                                     # Заводские настройки
        self.port.flushInput()
    
        self.PulseArmed = False                                                                                         # Никаких сука импульсов

        self.port.write(b":SENS:CURR:NPLC 10;\n")                                                                       # Магия мануальная
        self.port.write(b":SOUR:FUNC VOLT;\n") 
        self.port.write(b":SOUR:VOLT:MODE FIXED;\n") 
        self.port.write(b":SENS:FUNC \"CURR\";\n") 
        self.port.write(b":SENS:FUNC:CONC ON;\n") 
        s = ":SENS:CURR:PROT " + str(limit) + "; "
        self.port.write(s.encode('ascii')) 
        self.port.write(b":FORM:ELEM VOLT,CURR;\n") 
        self.port.write(b":SOUR:CLE:AUTO ON;\n")  
        self.port.write(b":SOUR:VOLT:RANGE:AUTO ON;\n")

        if autorange:
            self.port.write(b":SENS:CURR:RANGE:AUTO ON;\n")
        else:
            s = ":SENS:CURR:RANGE " + str(range) + ";\n"
            self.port.write(s.encode('ascii'))
        
        if remoteSensing:
            self.port.write(b":SYST:RSEN ON;\n")
        else:
            self.port.write(b":SYST:RSEN OFF;\n")      

        self.DCArmed = True                                                                                             # К измерениям готов!
        print("DC Armed")
        self.port.flushInput()
        time.sleep(2)                                                                                                   # Костыль, ждём две секунды чтоб прибор протупился
        return True

    # Realtime Pulse Sweep
    def armPulseMeasurements(self, remoteSensing=True, range=1e-3, limit=1.0, pulseWidth=1e-3, pulseDelay=1e0):         # Готовим импульсные измерения, всё почти так же, как и для постояного тока
        if self.port.closed:
            return False

        self.port.write(b"*RST;\n")
        self.port.flushInput()

        self.DCArmed = False

        if remoteSensing:
            self.port.write(b":SYST:RSEN ON;\n")
        else:
            self.port.write(b":SYST:RSEN OFF;\n")
       
        self.port.write(b":SOUR:FUNC:SHAP PULS;\n")
        s = ":SOUR:PULS:WIDTH " + str(pulseWidth) + ";\n"
        self.port.write(s.encode('ascii'))          
        s = ":SOUR:PULS:DELAY " + str(pulseDelay) + ";\n" 
        self.port.write(s.encode('ascii'))          
        self.port.write(b":SOUR:FUNC VOLT; \n")          
        self.port.write(b":SOUR:VOLT:RANG:AUTO ON; \n")
        self.port.write(b":SOUR:VOLT:MODE FIXED; \n")
        self.port.write(b":SENS:FUNC \"CURR\"; \n")
        self.port.write(b":SENS:FUNC:CONC ON;\n")
        self.port.write(b":SENS:CURR:NPLC 0.1; \n")
        s = ":SENS:CURR:PROT " + str(limit) + "; \n"
        self.port.write(s.encode('ascii'))
        s = ":SENS:CURR:RANG " + str(range) + "; \n"
        self.port.write(s.encode('ascii'))
        self.port.write(b":FORM:ELEM VOLT,CURR; \n")
        self.port.write(b":SYST:AZER ON;\n")

        self.PulseArmed = True
        print("Pulse Armed")        
        self.port.flushInput()
        time.sleep(2)
        return True   
        
    def getPoint(self, voltage=1.0, repeats=2):                                                                         # Хватаем точку
        if not self.DCArmed and not self.PulseArmed:
            return False                                                                                                # Если прибор ни к одним измерениям не готов, валим боком
         
        if self.port.closed:
            return False                                                                                                # Впрочем при закрытом порте тоже
   
        s = ":TRIG:COUN " + str(repeats) + "; \n"                                                                       # Задаём количесвто измерениц
        self.port.write(s.encode('ascii'))          
        s = ":SOUR:VOLT:LEV " + str(voltage) + "; \n"                                                                   # Задаём напряжение
        self.port.write(s.encode('ascii'))          
        s = ":INIT; \n"                                                                                                 # ЗАПУСКАЙ
        self.port.write(s.encode('ascii'))
        s = "*OPC?; \n"                                                                                                 # Прибор готов нам данные посылать?
        self.port.write(s.encode('ascii'))        
        
        while not b'1' in self.port.readline():                                                                         # Тупим, пока прибор измеряет
            time.sleep(0)
            
        s = ":FETCH?; \n"                                                                                               # Ловим точки
        self.port.write(s.encode('ascii'))

        #time.sleep(1)
        
        dataPoint = [0.0, 0.0]
        t = []
        
        #not exactly pretty
        p = b""                                                                                                         # Собираем точки костыльным образом
        while len(t) < repeats*2:
            p += self.port.readline()
            print(p.decode("ascii"))
            t = p.split(b",")
        #time.sleep(5)    
        for i in range(0, len(t), 2):    
            try:
                dataPoint[0] += float(t[i])
                dataPoint[1] += float(t[i+1])
            except ValueError:
                pass
        dataPoint[0] /= repeats
        dataPoint[1] /= repeats
        time.sleep(1)        
        return dataPoint                                                                                                # Отдаём полученную точку


# Keithley 2635a
class Keithley_2635a(Keithley):                                                                                         # Работаем с прибором 2635А
                                                                                                                        # Он кароч умеет только по старинке, и у него другой набор команд, а так - всё то же самое.
    """Keithley 2635A I-V Measurement Class"""

    def __init__(self, port, supportPulse):
        self.type = '2635A'
        self.port = port
        self.port.open()
        self.supportPulse = supportPulse
    
    def __del__(self):
        self.port.close()

    def doLegacySweep(self, startV=0.0, endV=3.0, numberOfPoints=100, remoteSensing=True, logSteps=False,
                      autorange=True, range=1e-3, limit=1.0, pulseSweep=False, pulseWidth=1e-3, pulseDelay=1e0):        # Вот наша старинка
        if self.port.closed:
            return False
        if not self.supportPulse and pulseSweep:
            return False
        self.port.write(b"reset(); smua.nvbuffer1.clear(); errorqueue.clear(); \n")                                     # Сбрасываем настройки
        s = "smua.source.limiti = " + str(limit) + ';\n'
        self.port.write(s.encode('ascii'))
    
        if autorange and not pulseSweep:                                                                                # Ограничения, авто
            self.port.write(b"smua.measure.autorangei = smua.AUTORANGE_ON; smua.measure.lowrangei = 10e-12;\n")
            self.port.write(b"smua.measure.autorangev = smua.AUTORANGE_ON; smua.measure.lowrangev = 10e-12;\n")
            self.port.write(b"smua.source.autorangei = smua.AUTORANGE_ON; smua.source.lowrangei = 10e-9;\n")
            self.port.write(b"smua.source.autorangev = smua.AUTORANGE_ON; smua.source.lowrangev = 10e-9;\n")
        else:                                                                                                           # Ограничение, неавто
            s = "smua.measure.autorangev = smua.AUTORANGE_OFF;smua.measure.autorangei = smua.AUTORANGE_OFF; "
            s += "smua.measure.rangei = " + str(range) + ";\n"
            s += "smua.source.autorangei = smua.AUTORANGE_OFF;smua.source.autorangev = smua.AUTORANGE_OFF; "
            s += "smua.source.rangev = " + str(range) + ";\n"
            s += "smua.measure.autozero = smua.AUTOZERO_ONCE; \n"
            self.port.write(s.encode('ascii'))
        
        if remoteSensing:                                                                                               # 2х-4х проводная
            self.port.write(b"smua.sense = smua.SENSE_REMOTE; \n")
        else:
            self.port.write(b"smua.sense = smua.SENSE_REMOTE; \n")
    
        self.port.write(b"smua.source.output = smua.OUTPUT_ON; \n")
        self.port.write(b"smua.measure.nplc = 25; \n")
    
        s = "" 
    
        if not pulseSweep:                                                                                              # Постоянный ток
            if logSteps:
                s += "SweepVLogMeasureI(smua, "
            else:
                s += "SweepVLinMeasureI(smua, "
            s += str(startV) + ', ' + str(endV) + ', ' + str(0.1) + ', ' + str(numberOfPoints) + ');\n'
        else:                                                                                                           # Импульсный
            if logSteps:
                s += "f, msg = ConfigPulseVMeasureISweepLog"
            else:
                s += "f, msg = ConfigPulseVMeasureISweepLin"
            s += "(smua,0," + str(startV) + ', ' + str(stopV) + ', ' + str(limit) + ', ', + str(pulseWidth) + ', ' \
                 + str(pulseDelay) + ', ' + str(numPoints) + "smua.nvbuffer1, 1)"
            s += "smua.nvbuffer1.appendmode=1; \n"
            s += "f1, msg1 = InitiatePulseTest(1);" 
            s += "smua.source.output = smua.OUTPUT_OFF\n"

        self.port.write(s.encode('ascii'))                                                                              # МАХМУД, ПОДЖИГАЙ
        self.port.write(b"smua.source.output = smua.OUTPUT_OFF; \n")                                                    # СУКА ТУШИ ГОРИТ ЖЕЖ

        return True
    
    def legacyReadDataPoints(self, numberOfPoints):                                                                     # Читаем точки по старинке!
        self.port.flushInput()
        dataPoints = []
        for i in range(1, numberOfPoints+1):
            s = "printbuffer(" + str(i) + ", " + str(i) + ", smua.nvbuffer1.sourcevalues,smua.nvbuffer1.readings); \n"
            self.port.write(s.encode('ascii'))
        
            p = self.port.readline()
        
            l = []
            for t in p.split(b","):
                try:
                    l.append(float(t))
                except ValueError:
                    pass
            dataPoints.append(l)
        return dataPoints         