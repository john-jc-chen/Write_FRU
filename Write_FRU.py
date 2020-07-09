import subprocess
import re
import argparse
import sys
import os
from os import path
import time
import copy
from telnetlib import Telnet
import logging

serial_Maps = {'MBM-XEM-002':{'VD185S003732':'S15317609627055'},'MBM-XEM-100':{'OD199S020072':'S308088X0116444'},'CMM-001':{'VD191S0000329':'S15317609627055'}}
bins = {'MBM-XEM-002':'FRU_MBM_XEM_002_V201_6.bin', 'CMM-001':'FRU_MBM_CMM_001_V102_2.bin', 'CMM-003':'FRU_MBM_CMM_FIO_V100_6.bin', 'MBM-XEM-100':'FRU_MBM_XEM_100_V101_6.bin'}

inter_files = []
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO , filename='Write_FRU.log')
def create_new_bin(model, bn):
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
    if bn not in map.keys():
        print("Can not find this serial number {} in database. Skip programming!!\n".format(bn))
        logging.error("Can not find this serial number {} in database. Skip programming!!".format(bn))
        return None
    else:
        sn = map[bn]
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

def Write_FRU(ip,username,passwd,bin_file,bn,slot):
    slot_map = {'CMM':'1' ,'A1':'3', 'A2':'4', 'B1':'5', 'B2':'6', 'CMM2':'18'}
    if sys.platform.lower() == 'win32':
        tool_dir = 'tool'
        tool_cmd = f'{tool_dir}\ipmitool.exe'
    else:
        tool_cmd = 'ipmitool'
    com = [tool_cmd, '-H', ip, '-U', username, '-P', passwd]
    c1 = copy.deepcopy(com)

    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x0'])
    if slot != 'CMM' and slot != 'CMM2':
        slot_txt = '0x' + slot.lower()
        run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '0'])
    run_ipmi(c1 + ['fru', 'write', slot_map[slot], bin_file])
    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x1'])
    if slot != 'CMM' and slot != 'CMM2':
        run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '1'])
    (board_serial, product_serial) = get_serial(com, slot_map[slot])
    if board_serial == bn:
        if not product_serial:
            print("Product serial mismatch after programming. Failed to write product serial on {}.\n".format(slot))
            logging.warning("Product serial mismatch after programming. Failed to write product serial on {}".format(bn))
        else:
            print("Updated FRU on {} successfully\n".format(slot))
            logging.info("Updated FRU on {} successfully.".format(bn))
    else:
        print("Board serial mismatch after programming. Failed to write board serial on {}.\n".format(slot))
        logging.warning("Board serial mismatch after programming. Failed to write board serial on {}".format(bn))


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
    else:
        print("Failed to login to CMM. Please check your user name and password.\n")
        logging.error("Failed to login to CMM. Please check your user name and password.")
        sys.exit()
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
def Write_device(ip, Username, Passwd, slot, model, bn):
    slot_map = {'CMM': '1', 'A1': '3', 'A2': '4', 'B1': '5', 'B2': '6', 'CMM2': '18'}
    if sys.platform.lower() == 'win32':
        tool_dir = 'tool'
        tool_cmd = f'{tool_dir}\ipmitool.exe'
    else:
        tool_cmd = 'ipmitool'
    com = [tool_cmd, '-H', ip, '-U', Username, '-P', Passwd]
    board_serial = ''
    product_serial = ''
    (board_serial, product_serial) = get_serial(com, slot_map[slot])
    if slot == 'CMM':
        if board_serial:
            if re.search(r'^0+$', board_serial):
                board_serial = ''
        else:
            board_serial = ''
        if product_serial:
            if re.search(r'^0+$', product_serial):
                product_serial = ''
        else:
            product_serial = ''
        # if int(board_serial) == 0:
        #     board_serial = ''
        # if int(product_serial) == 0:
        #     product_serial = ''
    #print(board_serial, product_serial, slot)
    if board_serial and product_serial:
        print("There is Board Serial and Product Serial on the device. Skip programming serial numbers on this device {}.\n Please check the information via Web GUI\n".format(slot))
        logging.warning("There is Board Serial and Product Serial on the device. Skip programming serial numbers on this device {}.".format(bn))
    else:
        bin_file = create_new_bin(model, bn)
        if not bin_file:
            print("Failed to programming on this device {}.\n".format(slot))
            logging.warning("Failed to generate .bin file on this device {}.".format(bn))
            return
        Write_FRU(ip, Username, Passwd, bin_file,bn,slot)
        while inter_files:
            bin = inter_files.pop()
            if sys.platform.lower() == 'win32':
                cmd = 'del ' + bin
            else:
                cmd = 'rm ' + bin
            os.system(cmd)

def check_connectivity(ip):

    logging.info("ping to  {}.".format(ip))
    if sys.platform.lower() == 'win32':
        res = subprocess.run(['ping','-n','3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        res = subprocess.run(['ping', '-c', '3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode  != 0:
        logging.warning("Failed to ping to  {}.".format(ip))
        return False
    else:
        out_text = res.stdout.decode("utf-8", errors='ignore')
        #print(out_text)
        if 'Destination host unreachable' in out_text:
            logging.warning("Destination host unreachable at {}.".format(ip))
            return False
        else:
            return True
def telnet_to_switch(ip):
    model = ''
    board_number = ''
    tn = Telnet(ip)
    tn.read_until(b"SMIS login:")
    tn.write("ADMIN".encode("utf-8") + b"\r\n")
    tn.read_until(b"Password:")
    tn.write("ADMIN".encode("utf-8") + b"\r\n")
    tn.read_until(b"SMIS#")
    tn.write("show version".encode("utf-8") + b"\r\n")
    lines = tn.read_until(b"SMIS#", 2).decode("utf-8", errors='ignore').split("\n")
    for i in range(len(lines)):
        if 'Hardware Version' in lines[i]:
            model = lines[i + 1].split()[1]
            break
    tn.write("show system info".encode("utf-8") + b"\r\n")
    lines = tn.read_until(b"SMIS#", 1).decode("utf-8", errors='ignore').split("\n")
    board_number = ''
    for line in lines:
        result = re.search(r'^Switch\s+Serial\s+Number\s+\:(.*?)$', line)
        if result:
            board_number = result.group(1).rstrip().lstrip()
            break
        result = re.search(r'^Serial\s+Number\s+\:(.*?)$', line)
        if result:
            board_number = result.group(1).rstrip().lstrip()
            break
    tn.write("ex".encode("utf-8") + b"\r\n")
    tn.close()
    return (model, board_number)

def main():
    data = {}
    try:
        #with open('SW_config.txt', 'r') as file:
        with open(sys.argv[1], 'r') as file:
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
        passwd = data['CMM Password']
    else:
        print("CMM Password is missing. Leave program!")
        sys.exit()

    if not check_connectivity(ip):
        print("Failed to access to CMM {}. Please check the connectivity and run this script again. Leave program!!.\n".format(ip))
        sys.exit()
    print('Checking connectivity and collecting data\n')
    if sys.platform.lower() == 'win32':
        tool_dir = 'tool'
        tool_cmd = f'{tool_dir}\ipmitool.exe'
    else:
        tool_cmd = 'ipmitool'
    com = [tool_cmd, '-H', ip, '-U', username, '-P', passwd]
    devices = []
    if 'A1 User Name' in data.keys():
        if 'A1 Password' in data.keys():
            try:
                output = subprocess.run(com + ['raw', '0x30', '0x33','0x0b', '0xa1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                print("Error has occurred in read data from CMM. Skip programming A1.\n")
                logging.error("Error has occurred in reading A1 IP. " + str(e))

            A1_ip = ''
            if output.returncode == 0:
                ip_text_ary = output.stdout.decode("utf-8", errors='ignore').split()[1:]
                for i in ip_text_ary:
                    A1_ip = A1_ip + str(int(i, 16)) + '.'
                A1_ip = A1_ip.rstrip(".")
            else:
                print("Error has occurred in read data from CMM. Skip programming A1.\n")
                logging.error("Fail to read A1 IP." + output.stderr.decode("utf-8", errors='ignore'))
            if check_connectivity(A1_ip):
                (model, board_number) = telnet_to_switch(A1_ip)
                if model and board_number:
                    devices.append("A1\t{}\t{}".format(board_number, model))
                else:
                    print("Failed to get board serial number on A1. Skip programming A1!.\n")
                    logging.error("ailed to get board serial number on A1. Skip programming A1!")
            else:
                print("Failed to access to A1 {}. Skip programming A1!.\n".format(A1_ip))
                logging.error("Fail to access to A1 {}. Skip programming A1!".format(A1_ip))

        else:
            print("A1 Password is missing. Skip programming switch in A1!\n")

    if 'A2 User Name' in data.keys():
        if 'A2 Password' in data.keys():
            try:
                output = subprocess.run( com + ['raw', '0x30', '0x33','0x0b', '0xa2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                print("Error has occurred in read data from CMM. Skip programming A2.\n")
                logging.error("Error has occurred in reading A2 IP. " + str(e))

            A2_ip = ''
            if output.returncode == 0:
                ip_text_ary = output.stdout.decode("utf-8", errors='ignore').split()[1:]
                for i in ip_text_ary:
                    A2_ip = A2_ip + str(int(i, 16)) + '.'
                A2_ip = A2_ip.rstrip(".")
            else:
                print("Error has occurred in read data from CMM. Skip programming A2.\n")
                logging.error("Fail to read A2 IP." + output.stderr.decode("utf-8", errors='ignore'))
            if check_connectivity(A2_ip):
                (model, board_number) = telnet_to_switch(A2_ip)
                if board_number and model:
                    devices.append("A2\t{}\t{}".format(board_number, model))
                else:
                    print("Failed to get board serial number on A2. Skip programming A2!\n")
                    logging.error("ailed to get board serial number on A2. Skip programming A2!")
            else:
                print("Failed to access to A2 {}. Skip programming A2!\n".format(A2_ip))
                logging.error("Fail to access to A2 {}. Skip programming A2!".format(A2_ip))

        else:
            print("A2 Password is missing. skip programming switch in A2!\n")

    # if 'A1' in data.keys():
    #     if data['A1 Model'] and data['A1 Model'] != '':
    #         devices.append("A1\t{}\t{}".format(data['A1'], data['A1 Model']))
    #     else:
    #         print("A1 Model is missing. Skip programming FRU on A1")
    #         logging.warning("A1 Model is missing. Skip programming FRU on A1")
    # if 'A2' in data.keys():
    #     if data['A2 Model'] and data['A2 Model'] != '':
    #         devices.append("A2\t{}\t{}".format(data['A2'], data['A2 Model']))
    #     else:
    #         print("A2 Model is missing. Skip programming FRU on A2")
    #         logging.warning("A2 Model is missing. Skip programming FRU on A2")
    # if 'CMM' in data.keys():
    #     if data['CMM Model'] and data['CMM Model'] != '':
    #         devices.append("CMM\t{}\t{}".format(data['CMM'], data['CMM Model']))
    #     else:
    #         print("CMM Model is missing. Skip programming FRU on CMM")
    #         logging.warning("CMM Model is missing. Skip programming FRU on CMM")

    #print(devices)
    for dev in devices:
        (slot,bn, model) = re.split(r'\t', dev)
        print("Programming FRU on device in {}".format(slot))
        logging.info("Programming FRU {} in {}".format(bn,slot))
        Write_device(ip, username, passwd, slot, model, bn)


if __name__ == '__main__':
    main()
