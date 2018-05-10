import serial
import re
import pdb

# ToDo | 1. Test new functions
# ToDo | 2. See if the floats that come in are correct (the pump will probably
# ToDo |    complain if not)


def find_pumps(ser, tot_range=10):
    pumps = []
    for i in range(tot_range):
        cmd = '%iADR\x0D' % i
        ser.write(cmd.encode())
        output = ser.readline().decode()
        if len(output) > 0:
            pumps.append(i)
    return pumps


def error_handler(fcn, msg):  # See page 36/pp 41 in manual
    # print('error_handler with fcn={}, msg={}'.format(fcn, msg))
    if not msg:
        return 'Command in {} not recognized'.format(fcn)
    elif 'NA' in msg:
        return 'Command not applicable. Command in {}'.format(fcn)
    elif 'OOR' in msg:
        return 'Command data out of range. Command in {}'.format(fcn)
    elif 'COM' in msg:
        return 'Invalid packet received. Command in {}'.format(fcn)
    elif 'IGN' in msg:
        return 'Command ignored. Command in {}'.format(fcn)
    else:
        return 'Command in {} not understood'.format(fcn)


# TRY THIS ONE OUT
def reset_all(ser):
    cmd = '*RESET\x0D'
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from reset_all not understood')
        print(error_handler(fcn='reset_all', msg=output))


def run_all(ser):
    cmd = '*RUN\x0D'
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from run_all not understood')
        print(error_handler(fcn='run_all', msg=output))


def stop_all(ser):
    cmd = '*STP\x0D'
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from stop_all not understood')
        print(error_handler(fcn='stop_all', msg=output))


def stop_pump(ser, pump):
    cmd = '%iSTP\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from stop_pump not understood')
        print(error_handler(fcn='stop_pump', msg=output))

    cmd = '%iRAT0UH\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from stop_pump not understood')
        print(error_handler(fcn='stop_pump', msg=output))


def set_rates(ser, rate):
    cmd = ''
    for pump in rate:
        flowrate = float(rate[pump])
        if flowrate < 0:
            direction = 'WDR'
        else:
            direction = 'INF'
        frcmd = '%iDIR%s\x0D' % (pump, direction)
        ser.write(frcmd.encode())
        output = ser.readline().decode()
        if '?' in output:
            # print(frcmd.strip()+' from set_rate not understood')
            print(error_handler(fcn='set_rates', msg=output))
        fr = abs(flowrate)
                
        if fr < 5000:
            cmd += str(pump)+'RAT'+str(fr)[:5]+'UH*'
        else:
            fr = fr/1000.0
            cmd += str(pump)+'RAT'+str(fr)[:5]+'MH*'
    cmd += '\x0D'
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from set_rates not understood')
        print(error_handler(fcn='set_rates', msg=output))


def get_direction(ser, pump):
    # get direction
    cmd = '%iDIR\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    return 'INF' if 'INF' in output else 'WDR'


def is_inf(ser, pump):
    return True if 'INF' == get_direction(ser, pump) else False


def get_rate(ser, pump):
    sign = ''
    if not is_inf(ser, pump):
        sign = '-'
    cmd = '%iRAT\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from get_rate not understood')
        print(error_handler(fcn='get_rate', msg=output))

    pf = '(([0-9]|\.)*)(MH|UH|MM|UM)'
    m = re.search(pf, output)
    # User enters ul -> converted to ul/hr. Any rate might be in pump already.
    # Convert current rate to ul/hr
    # 1 ml = 1000 ul
    # 1 min = (1/60) hr
    if m:
        if 'MH' in output:  # ml/hr = 1000 ul/hr
            rate = str(float(m.group(1))*1000)
        elif 'UH' in output:  # ul/hr
            rate = m.group(1)
        elif 'MM' in output:  # ml/min = (1000*60) ul/hr
            rate = str(float(m.group(1))*1000*60.0)
        elif 'UM' in output:  # ul/min = 60 ul/hr
            rate = str(float(m.group(1))*60.0)
    else:  # Fail; return empty string -> evaluates to False
        sign = ''
        rate = ''
    return sign + rate


def get_rates(ser, pumps):
    rates = dict((p, get_rate(ser, p).split('.')[0]) for p in pumps)
    return rates


def set_diameter(ser, pump, dia):
    cmd = '%iDIA%s\x0D' % (pump, dia)
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from set_diameter not understood')
        print(error_handler(fcn='set_diameter', msg=output))

    
def get_diameter(ser, pump):
    cmd = '%iDIA\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from get_diameter not understood')
        print(error_handler(fcn='get_diameter', msg=output))
    dia = output[4:-1]
    return dia


def prime(ser, pump):
    # set infuse direction
    cmd = '%iDIRINF\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from prime not understood')
        print(error_handler(fcn='prime', msg=output))

    # set rate
    cmd = '%iRAT10.0MH\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from prime not understood')
        print(error_handler(fcn='prime', msg=output))

    # run
    cmd = '%iRUN\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        # print(cmd.strip()+' from prime not understood')
        print(error_handler(fcn='prime', msg=output))


def set_volume(ser, pump, vol):
    # Using VOL to set volume to be dispensed
    cmd = '%iVOL%s\x0D' % (pump, vol)
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        print(error_handler(fcn='set_volume', msg=output))
        # print(cmd.strip()+' from set_volume not understood')


def get_volume(ser, pump):
    # Using VOL to get volume to be dispensed
    cmd = '%iVOL\x0D' % pump
    ser.write(cmd.encode())
    p = '(S)(([0-9]|\.)*)(UL|ML)'
    output = ser.readline().decode()
    if '?' in output:
        print(error_handler(fcn='get_volume', msg=output))
        # print(cmd.strip() + ' from get_volume not understood')
    m = re.search(p, output)
    if m:
        return m.group(2)
    else:
        return ''


# TRY THIS ONE OUT
def set_volume_units(ser, pump, units):
    # Using VOL to get volume to be dispensed
    cmd = '%iVOL%s\x0D' % (pump, units)
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        print(error_handler(fcn='set_volume_units', msg=output))
        # print(cmd.strip()+' from set_volume_units not understood')


def get_volume_units(ser, pump):
    # Using VOL to get volume to be dispensed
    cmd = '%iVOL\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    m = re.search('(UL|ML)', output)
    if '?' in output:
        print(error_handler(fcn='get_volume_units', msg=output))
        # print(cmd.strip()+' from get_volume_units not understood')
    if m:
        return m.group(0)
    else:
        return ''


def get_dis(ser, pump):
    cmd = '%iDIS\x0D' % pump  # DIS gets the volumes that have been dispensed
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        print(error_handler(fcn='get_dispensed', msg=output))
        # print(cmd.strip() + ' from get_dispensed not understood')
    return output


def get_dispensed(ser, pump, dis=None):
    output = get_dis(ser, pump)
    # Output format 'I<float>W<float><volume units>'
    p = '(I)(([0-9]|\.)*)(W)(([0-9]|\.)*)([A-Z][A-Z])'  # Match pattern
    m = re.search(p, output)
    if '?' in output or not m:
        return ''  # Evaluates to None
    elif m:
        if dis == 'INF':  # Querying infused volume
            return m.group(2)
        elif dis == 'DIS':  # Querying withdrawn volume
            return m.group(5)
        elif dis is None:  # Querying both
            return m.group(2, 5)
    else:
        return ''  # Safeguard


# Haven't figured out how to work with it right now
def clear_dispensed(ser, pump):
    cmd = '%iCLD\x0D' % pump
    ser.write(cmd.encode())
    output = ser.readline().decode()
    if '?' in output:
        print(error_handler(fcn='clear_dispensed', msg=output))
        # print(cmd.strip() + ' from clear_dispensed not understood')


# UNDER CONSTRUCTION
# From the manual:
#   "The Fill function reverses the pumping direction and withdraws or
#    dispenses [or infuses] the volume dispensed [or infused] or withdrawn."
# Try this --> set vol,
#              set: dispensed volume = 0
#             then: run (assuming proper rate is set)
# and that will hopefully pump at given rate until volume has been dispensed
# and then we should be able to use this to just run 'FIL' again
# def fill_syringe(ser, pump):
#     cmd = '%iFUNFIL\x0D' % pump
#     ser.write(cmd.encode())
#     output = ser.readline().decode()
#     if '?' in output:
#         print(error_handler(fcn='fill_syringe', msg=output))
        # print(cmd.strip() + ' from fill_syringe not understood')


# ser = serial.Serial('COM3',19200, timeout=.1)
# ser = serial.Serial('/dev/ttyUSB0', 19200, timeout=.1)
# print(ser.name)  # check which port was really used
# print(ser.isOpen())
# ser.close()
# pdb.set_trace()
# pumps = find_pumps(ser)
# rates = get_rates(ser, pumps)
