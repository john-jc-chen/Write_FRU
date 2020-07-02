import subprocess
import re
import argparse
import sys
import os
from os import path
import time
import copy
import logging

logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO , filename='Write_FRU.log')
serial_Maps = {'MBM-XEM-002':{'S15317609627055':'VD191S000329'},'MBM-XEM-100':{'S308088X0116444':'OD19S020072'},'CMM-001':{'S15317609627055':'VD191S0000329'}}
bins = {'MBM-XEM-002':'FRU_MBM_XEM_002_V201_6.bin', 'CMM-001':'FRU_MBM_CMM_001_V102_2.bin', 'CMM-003':'FRU_MBM_CMM_FIO_V100_6.bin', 'MBM-XEM-100':'FRU_MBM_XEM_100_V101_6.bin'}
inter_files = []

def create_new_bin(model, sn):
    if sys.platform.lower() == 'win32':
        bin = 'bin\\'+ bins[model]
    else:
        bin = 'bin/{}'.format(bins[model])
    if model not in serial_Maps.keys():
        print("Error Model name. Skip programming!!")
        logging.error("Error Model name. Skip programming!!")
        return None
    else:
        map = serial_Maps[model]
    if sn not in map.keys():
        print("Can not find this serial number {} in database. Skip programming!!".format(sn))
        logging.error("Can not find this serial number {} in database. Skip programming!!".format(sn))
        return None
    else:
        bn = map[sn]
    new_bin = ""
    new_bin = run_ModifyFRU(bin, 'bs', bn)
    #print(new_bin)
    inter_files.append(new_bin)
    new_bin = run_ModifyFRU(new_bin, 'ps', sn)

    if sys.platform.lower() == 'win32':
        file_name= sn + '.bin'
    else:
        file_name= "bin/{}.bin".format(sn)
    #print(new_bin)

    if not path.isfile(file_name):
        try:
            #subprocess.call(['ren', new_bin, file_name])
            if sys.platform.lower() == 'win32':
                os.system('ren {} {}'.format(new_bin, file_name))
            else:
                os.system('mv {} {}'.format(new_bin, file_name))
        except Exception as e:
            print("Error has occurred. eave program!!" + str(e))
            logging.error("Failed to rename this file {}. In create_new_bin.".format(new_bin) + str(e))
            sys.exit()

    if sys.platform.lower() == 'win32':
        inter_files.append('bin\\' + file_name)
        return 'bin\\' + file_name
    else:
        inter_files.append(file_name)
        return '{}'.format(file_name)

def run_ModifyFRU(file_name, type, serial):
    if sys.platform.lower() == 'win32':
        tool_dir = 'Windows'
        tool_cmd = f'{tool_dir}\ModifyFRU'
    else:
        tool_dir = 'Linux'
        tool_cmd = f'{tool_dir}/ModifyFRU'
    if type == 'bs':
        type = '--bs'
    if type == 'ps':
        type = '--ps'

    try:
        output = subprocess.run([tool_cmd, '-f', file_name, type, serial], stdout=subprocess.PIPE)
        # os.system(cmd)
    except Exception as e:
        print("Error has occurred in create bin with serial {}. Leave program!!".format(serial) + str(e))
        logging.error("Error has occurred in run_ModifyFRU with serial {}. ".format(serial) + str(e))
        sys.exit()
    #print(output)
    if output.returncode == 0:
        out_txt = output.stdout.decode("utf-8", errors='ignore')
        if sys.platform.lower() == 'win32':
            result = re.search(r'(bin\\.*?)$', out_txt)
            return result.group(1).rstrip()
        else:
            return "{}.new.{}".format(file_name, serial)
    else:
        print("Error has occurred in create bin with serial {}. Leave program!!".format(serial))
        logging.error("Error has occurred in run_ModifyFRU with serial {}. ".format(serial) + output.stderr.decode("utf-8", errors='ignore'))
        sys.exit()

def Write_FRU(ip,username,passwd,bin_file,sn,slot):
    slot_map = {'CMM1':'1' ,'A1':'3', 'A2':'4', 'B1':'5', 'B2':'6', 'CMM2':'18'}
    if sys.platform.lower() == 'win32':
        tool_dir = 'tool'
        tool_cmd = f'{tool_dir}\ipmitool.exe'
    else:
        tool_cmd = 'ipmitool'
    com = [tool_cmd, '-H', ip, '-U', username, '-P', passwd]
    c1 = copy.deepcopy(com)

    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x0'])
    if slot != 'CMM1' and slot != 'CMM2':
        slot_txt = '0x' + slot.lower()
        run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '0'])
    run_ipmi(c1 + ['fru', 'write', slot_map[slot], bin_file])
    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x1'])
    if slot != 'CMM1' and slot != 'CMM2':
        run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '1'])
    (board_serial, product_serial) = get_serial(com, slot_map[slot])
    if product_serial == sn:
        if not board_serial:
            print("Board serial mismatch. Failed to write Board Serial on {}".format(sn))
            logging.warning("Board serial mismatch. Failed to write Board Serial on {}".format(sn))
        else:
            print("Updated FRU on {} successfully\n".format(sn))
            logging.info("Updated FRU on {} successfully.".format(sn))
    else:
        print("Product serial mismatch. Failed to write Product Serial on {}".format(sn))
        logging.warning("Product serial mismatch. Failed to write Product Serial on {}".format(sn))


def get_serial(com, slot):
    com = com + ['fru', 'print', slot]
    output = subprocess.run(com, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    board_number = None
    product_number = None

    if output.returncode == 0:
        out_txt = output.stdout.decode("utf-8", errors='ignore')
        result = re.search(r'Board\s+Serial\s+\:\s?(\w+)', out_txt)
        if result:
            board_number = result.group(1).rstrip().lstrip()
        result = re.search(r'Product\s+Serial\s+\:\s?(\w+)', out_txt)
        if result:
            product_number = result.group(1).rstrip().lstrip()
    #print("{} bs {} ps {}".format(out_txt, board_number, product_number))
    return (board_number, product_number)
def run_ipmi(com):

    try:
        output = subprocess.run(com, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # os.system(cmd)
    except Exception as e:
        print("Error has occurred in updating FRU. " + str(e))
        sys.exit()
    #print(output)
def Write_device(ip, Username, Passwd, slot, model, sn):
    slot_map = {'CMM1': '1', 'A1': '3', 'A2': '4', 'B1': '5', 'B2': '6', 'CMM2': '18'}
    if sys.platform.lower() == 'win32':
        tool_dir = 'tool'
        tool_cmd = f'{tool_dir}\ipmitool.exe'
    else:
        tool_cmd = 'ipmitool'
    com = [tool_cmd, '-H', ip, '-U', Username, '-P', Passwd]
    board_serial = ''
    product_serial = ''
    (board_serial, product_serial) = get_serial(com, slot_map[slot])
    #print(board_serial, product_serial, slot)
    if board_serial and product_serial:
        print("There is Board Serial and Product Serial on the device. Skip programming serial numbers on this device {}.\n Please check the information via Web GUI".format(sn))
        logging.warning("There is Board Serial and Product Serial on the device. Skip programming serial numbers on this device {}.\n Please check the information via Web GUI".format(sn))
    else:
        bin_file = create_new_bin(model, sn)
        if not bin_file:
            return
        Write_FRU(ip, Username, Passwd, bin_file,sn,slot)
        while inter_files:
            bin = inter_files.pop()
            if sys.platform.lower() == 'win32':
                cmd = 'del ' + bin
            else:
                cmd = 'rm ' + bin
            os.system(cmd)

def check_connectivity(ip):
    if sys.platform.lower() == 'win32':
        res = subprocess.run(['ping','-n','3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        res = subprocess.run(['ping', '-c', '3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode  != 0:
        return False
    else:
        out_text = res.stdout.decode("utf-8", errors='ignore')
        #print(out_text)
        if 'Destination host unreachable' in out_text:
            return False
        else:
            return True

def main():
    data = {}
    try:
        with open('SW_config.txt', 'r') as file:
            for line in file:
                result = re.match(r'^(\w+.*?)\:(.*?)$', line)
                if result:
                    value = result.group(2).rstrip().lstrip()
                    if value and value != '':
                        field = result.group(1).rstrip().lstrip()
                        field = re.sub(r'\(.*?\)', '', field)
                        data[field] = value
    except IOError as e:
        print("config file is not available. Please read readme file and run this program again. Leave program!")
        logging.error("config file is not available.")
        sys.exit()
    #print(data)


    if 'CMM IP' in data.keys():
        ip = data['CMM IP']
    else:
        print("CMM IP is missing. Leave program!")
        sys.exit()

    if 'CMM User Name' in data.keys():
        username =  data['CMM User Name']
    else:
        print("CMM user name is missing. Leave program!")
        sys.exit()

    if 'CMM Password' in data.keys():
        password = data['CMM Password']
    else:
        print("CMM Password is missing. Leave program!")
        sys.exit()

    if not check_connectivity(ip):
        print("Failed to access to {}. Leave program!!".format(ip))
        sys.exit()

    devices = []
    if 'A1' in data.keys():
        if data['A1 Model'] and data['A1 Model'] != '':
            devices.append("A1\t{}\t{}".format(data['A1'], data['A1 Model']))
        else:
            print("A1 Model is missing. Skip programming FRU on A1")
            logging.warning("A1 Model is missing. Skip programming FRU on A1")
    if 'A2' in data.keys():
        if data['A2 Model'] and data['A2 Model'] != '':
            devices.append("A2\t{}\t{}".format(data['A2'], data['A2 Model']))
        else:
            print("A2 Model is missing. Skip programming FRU on A2")
            logging.warning("A2 Model is missing. Skip programming FRU on A2")
    if 'B1' in data.keys():
        if data['B1 Model'] and data['B1 Model'] != '':
            devices.append("B1\t{}\t{}".format(data['B1'], data['B1 Model']))
        else:
            print("B1 Model is missing. Skip programming FRU on B1")
            logging.warning("B1 Model is missing. Skip programming FRU on B1")
    if 'B2' in data.keys():
        if data['B2 Model'] and data['B2 Model'] != '':
            devices.append("B2\t{}\t{}".format(data['B2'], data['B2 Model']))
        else:
            print("B2 Model is missing. Skip programming FRU on B2")
            logging.warning("B2 Model is missing. Skip programming FRU on B2")
    #print(devices)
    for dev in devices:
        (slot,sn, model) = re.split(r'\t', dev)
        print("Programming FRU on {} in {}".format(sn,slot))
        logging.info("Programming FRU on {} in {}".format(sn,slot))
        Write_device(ip, username, password, slot, model, sn)


if __name__ == '__main__':
    main()
