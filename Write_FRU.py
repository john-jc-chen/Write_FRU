import subprocess
import re
import argparse
import sys
import os
from os import path
import time
import copy
import logging


serial_Maps = {'MBM-XEM-002':{'S196050X9A25291':'VD197S001463'},'MBM-XEM-100':{'S308088X9A04247':'OD198S039395'},'CMM':{}}
bins = {'MBM-XEM-002':'FRU_MBM_XEM_002_V201_6.bin', 'CMM':'', 'MBM-XEM-100':'FRU_MBM_XEM_100_V101_6.bin'}
inter_files = []

def create_new_bin(model, sn):
    bin = 'bin\\'+ bins[model]
    map = serial_Maps[model]
    bn = map[sn]

    new_bin = run_ModifyFRU(bin, 'bs', bn)
    #print(new_bin)
    inter_files.append(new_bin)
    new_bin = run_ModifyFRU(new_bin, 'ps', sn)
    file_name= sn + '.bin'
    try:
        #subprocess.call(['ren', new_bin, file_name])
        os.system('ren {} {}'.format(new_bin, file_name))
    except Exception as e:
        print("Error has occured. " + str(e))
        sys.exit()
    inter_files.append('bin\\' + file_name)
    return 'bin\\' + file_name

def run_ModifyFRU(file_name, type, serial):
    tool_dir = 'Windows'
    tool_cmd = f'{tool_dir}\ModifyFRU'
    if type == 'bs':
        type = '--bs'
    if type == 'ps':
        type = '--ps'
    #print('tool_cmd: {} serial:{} type:{} file_name:{}'.format(tool_cmd, serial, type, file_name))
    try:
        output = subprocess.run([tool_cmd, '-f', file_name, type, serial], stdout=subprocess.PIPE)
        # os.system(cmd)
    except Exception as e:
        print("Error has occured in create bin with serial {}. ".format(serial) + str(e))
        sys.exit()
   # print(output)
    if output.returncode == 0:
        out_txt = output.stdout.decode("utf-8", errors='ignore')
        result = re.search(r'(bin\\.*?)$', out_txt)
        return result.group(1).rstrip()
    else:
        print("Error has occured in create bin with serial {}. ".format(serial))
        #print("Error has occured in create bin with serial {}. ".format(serial) + output.stdout.decode("utf-8", errors='ignore'))
        sys.exit()

def Write_FRU(ip,username,passwd,bin_file,sn,slot):
    slot_map = {'CMM1':'1' ,'A1':'3', 'A2':'4', 'B1':'5', 'B2':'6', 'CMM2':'18'}
    tool_dir = 'tool'
    tool_cmd = f'{tool_dir}\ipmitool.exe'
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
            print("Failed to write Board Serial on {}".format(sn))
        # else:
        #     print("Board Serial and Product Serial are programmed on {}".format(sn))
    else:
        print("Failed to write Product Serial on {}".format(sn))


def get_serial(com, slot):
    com = com + ['fru', 'print', slot]
    output = subprocess.run(com, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    board_number = None
    product_number = None
    #print("out_txt {}".format(output))
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
        print("Error has occured in updating FRU. " + str(e))
        sys.exit()
    #print(output)
def Write_device(ip, Username, Passwd, slot, model, sn):
    #sn = 'S196050X9A25291'
    #model = 'XEM_002'

    sn = 'S308088X9A04247'
    model = 'MBM-XEM-100'
    ip = '172.31.51.91'
    Username = 'ADMIN'
    Passwd = 'ADMIN'
    #slot = 'A2'
    slot = 'A1'
    slot_map = {'CMM1': '1', 'A1': '3', 'A2': '4', 'B1': '5', 'B2': '6', 'CMM2': '18'}
    tool_dir = 'tool'
    tool_cmd = f'{tool_dir}\ipmitool.exe'
    com = [tool_cmd, '-H', ip, '-U', Username, '-P', Passwd]

    (board_serial, product_serial) = get_serial(com, slot_map[slot])
    if board_serial or product_serial:
        print("There is Board Serial or Product Serial in the FRU. Skip programming serial numbers on this device {}.\n Please check the information via Web GUI".format(sn))
    else:
        bin_file = create_new_bin(model, sn)
        Write_FRU(ip, Username, Passwd, bin_file,sn,slot)
        for bin in inter_files:
            cmd = 'del ' + bin
            os.system(cmd)
        print("Updated FRU on {} successfully\n".format(sn))

def main():

    data = {}
    try:
        with open('config.txt', 'r') as file:
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
        sys.exit()
    #print(data)

    if 'CMM1 IP' in data.keys:
        ip =  data['CMM1 IP']
    else:
        print("CMM1 IP is missing. Leave program!")
        sys.exit()

    if 'CMM1 User Name' in data.keys:
        username =  data['CMM1 User Name']
    else:
        print("CMM1 user name is missing. Leave program!")
        sys.exit()

    if 'CMM1 Password' in data.keys:
        password = data['CMM1 Password']
    else:
        print("CMM1 Password is missing. Leave program!")
        sys.exit()

    devices = []
    if 'A1' in data.keys():
        if data['A1 Model'] and data['A1 Model'] != '':
            devices.append("A1\t{}\t{}".format(data['A1'], data['A1 Model']))
        else:
            print("A1 Model is missing. Skip programming FRU on A1")
    if 'A2' in data.keys():
        if data['A2 Model'] and data['A2 Model'] != '':
            devices.append("A2\t{}\t{}".format(data['A2'], data['A2 Model']))
        else:
            print("A2 Model is missing. Skip programming FRU on A2")
    if 'B1' in data.keys():
        if data['B1 Model'] and data['B1 Model'] != '':
            devices.append("B1\t{}\t{}".format(data['B1'], data['B1 Model']))
        else:
            print("B1 Model is missing. Skip programming FRU on B1")
    if 'B2' in data.keys():
        if data['B2 Model'] and data['B2 Model'] != '':
            devices.append("B2\t{}\t{}".format(data['B2'], data['B2 Model']))
        else:
            print("B2 Model is missing. Skip programming FRU on B2")
    if 'CMM1 Product Serial Number' in data.keys():
        devices.append("CMM1\t{}\tCMM".format(data['CMM1']))

    for dev in devices:
        (slot, model, sn) = re.split(r'\t', dev)
        print("Programming FRU on {}".format(sn))
        Write_device(ip, username, password, slot, model, sn)

    if 'CMM2 IP' in data.keys:
        ip = data['CMM2 IP']
        if 'CMM2 User Name' in data.keys:
            username = data['CMM2 User Name']
        else:
            print("CMM2 user name is missing. Leave program!")
            sys.exit()

        if 'CMM2 Password' in data.keys:
            password = data['CMM2 Password']
        else:
            print("CMM2 Password is missing. Leave program!")
            sys.exit()

        if 'CMM2 Product Serial Number' in data.keys():
            Write_device(ip, username, password, 'CMM2', 'CMM', data['CMM2 Product Serial Number'])
        else:
            print("CMM2 Product Serial Number is missing. Leave program!")
            sys.exit()

if __name__ == '__main__':
    main()
