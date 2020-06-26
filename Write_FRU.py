import subprocess
import re
import argparse
import sys
import os
from os import path
import time
import copy

serial_Maps = {'XEM_002':{'S196050X9A25291':'VD197S001463'},'25G_100':{'S308088X9A04247':'OD198S039395'},'XEM_100':{}}
bins = {'XEM_002':'FRU_MBM_XEM_002_V201_6.bin', '25G_100':'FRU_SBM_25G_100_V101_6.bin', 'XEM_100':'FRU_MBM_XEM_100_V101_6.bin'}

#with SUM, change all IP in the ip file create to the password file, using the unique passwords
def change_password(ip_to_password, password_file):
    try:
        tool_dir = os.environ["SUM_DIR"]
    except KeyError:
        msg = " **** ERROR **** Environment variable SUM_DIR is not set"
        print(msg)
        sys.exit()
    tool_cmd = f'{tool_dir}/sum'
    try:
        with open("ip.txt",'r') as f:
            with open(password_file,'r') as new_password:
                for each_entry in f:
                    ip = each_entry
                    print(f'{ip}')
                    password = ip_to_password[ip.strip()].strip()
                    ip = ip.strip()
                    subprocess.call([tool_cmd, '-i', ip, '-u', 'ADMIN','-p', password, '-c',
                                     'SetBmcPassword', '--pw_file', password_file])
                    print('\n')
    except:
        print("Error has occured")
        sys.exit()
def create_new_bin(model, sn):
    bin = 'bin\\'+ bins[model]
    map = serial_Maps[model]
    bn = map[sn]

    new_bin = run_ModifyFRU(bin, 'bs', bn)
    #print(new_bin)
    new_bin = run_ModifyFRU(new_bin, 'ps', sn)
    file_name= sn + '.bin'
    try:
        #subprocess.call(['ren', new_bin, file_name])
        os.system('ren {} {}'.format(new_bin, file_name))
    except Exception as e:
        print("Error has occured. " + str(e))
        sys.exit()
    return file_name

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
    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x0'], sn)
    slot_txt = '0x' + slot.lower()
    run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '0'])
    run_ipmi(c1 + ['fru', 'write', slot_map[slot], bin_file])
    run_ipmi(c1 + ['raw', '0x30', '0x6', '0x1'], sn)
    run_ipmi(c1 + ['raw', '0x30', '0x33', '0x28', slot_txt, '1'])
    run_ipmi(c1 + ['fru', 'print', slot_map[slot]])
def run_ipmi(com,sn):
    try:
        output = subprocess.run(com, stdout=subprocess.PIPE)
        # os.system(cmd)
    except Exception as e:
        print("Error has occured in updating FRU. " + str(e))
        sys.exit()

def main():
    sn = 'S196050X9A25291'
    model = 'XEM_002'
    ip = '192.168.100.110'
    Username = 'ADMIN'
    Passwd = 'ADMIN'
    slot = 'A1'
    bin_file = create_new_bin(model, sn)
    Write_FRU(ip, Username, Passwd, bin_file,sn,slot)

    print("{} successfully updated".format(sn))

if __name__ == '__main__':
    main()
