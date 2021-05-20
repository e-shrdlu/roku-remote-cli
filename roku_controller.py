import os
from pynput.keyboard import Key,Listener
from threading import Thread
import requests
import time
import urllib.parse
import argparse
import re
# import scapy.all as scapy

parser=argparse.ArgumentParser()
parser.add_argument("-c","--command",help="string to execute in mini command-line")
parser.add_argument("-i","--ip",help="ip of roku to use")
args=parser.parse_args()

# for reference: https://github.com/tispratik/docs-1/blob/master/develop/guides/remote-api-ecp.md

ip = '192.168.0.177' # DEBUG: mac is ac-3a-7a-ad-22-c9
# base_cmd = "curl -d '' {ip}:8060/keypress/{button}" # home,up,down,right,left. unconfirmed: back, a, b, pause
# also keypress and keydown
button_dict = {"Key.up":"up","Key.left":"left","Key.right":"right","Key.down":"down","Key.backspace":"back","Key.enter":"select","'p'":"play","'z'":"rew","'x'":"fwd","'i'":"info","'h'":"home"}
instant_mode=True
toggle_mode_key="Key.esc"
go=True
previous_command=''
help = "\n***************\n\nexit\texits\nhelp\tshows this text\nsend\t[keypress,keyup,keydown]/[left,right,etc ('help keys' to see all)]\nsendstr\t[string (everything after 'sendstr ' will be sent\nsendbtns\t[comma seperated buttons] [:time between pressed]\nquery\t [apps,active,info]\nlaunch\t{app id}\nchangeip\t[ip]\nfindroku\t[:set] scans network for roku, and optionally sets ip to first found\nsleep\t[int], default 1\n[int]\trepeats last cmd [int] times\n\n***************\n"
keys_list = 'keys:\n\nHome\nLeft\nInstantReplay\nRew(Rewind)\nRight\nInfo\nFwd\nDown\nBackspace\nPlay\nUp\nSearch\nSelect\nBack\nEnter\n\nroku TV only:\nVolumeDown\nVolumeMute\nVolumeUp'


def send(cmd):
    print(cmd)
    # return cmd + " would have been run"
    return os.system(cmd)

def exec_command(raw_input):
    global go, instant_mode, ip, previous_command, help, keys_list
    for user_input in raw_input.split(" && "):
        user_input_split = user_input.split(" ")

        if user_input_split[0] == "exit":
            go=False
            return 0
        elif user_input_split[0] == "help":
            if len(user_input_split) > 1 and user_input_split[1] == "keys":
                print(keys_list)
            else:
                print(help)
        elif user_input_split[0] == "send":
            if len(user_input_split) > 1:
                cmd = f"curl -d '' http://{ip}:8060/{user_input_split[1]}"
                send(cmd)
            else:
                print(help)
        elif user_input_split[0] == "query":
            if len(user_input_split) > 1:
                if user_input_split[1] == "apps":
                    cmd = f"curl http://{ip}:8060/query/apps"
                    send(cmd)
                elif user_input_split[1] == "active":
                    cmd = f"curl http://{ip}:8060/query/active-app"
                    send(cmd)
                elif user_input_split[1] == "info":
                    cmd = f"curl http://{ip}:8060/query/device-info"
                    send(cmd)
            else:
                print(help)
        elif user_input_split[0] == "launch":
            if len(user_input_split) > 1:
                app_id = user_input_split[1]
                cmd = f"curl -d '' http://{ip}:8060/launch/{app_id}"
                send(cmd)
            else:
                print(help)
        elif user_input_split[0] == "sendstr":
            if len(user_input_split) > 1:
                for char in user_input[8:]: # [8:] to not get 'sendstr' in string
                    encoded_char=urllib.parse.quote(char, safe="") # ' ' -> '%20', etc
                    cmd = f"curl -d '' http://{ip}:8060/keypress/Lit_{encoded_char}"
                    send(cmd)
            else:
                print(help)
        elif user_input_split[0] == "sendbtns":
            if len(user_input_split) > 1:
                for btn in user_input_split[1].split(','):
                    cmd = f"curl -d '' http://{ip}:8060/keypress/{btn}"
                    send(cmd)
                    if len(user_input_split) > 2 and user_input_split[2].isdigit():
                        time.sleep(int(user_input_split[2]))
            else:
                print(help)
        elif user_input_split[0].isdigit():
            for x in range(int(user_input_split[0])):
                print("repeating last command",x,"out of",user_input_split[0],"times.",100*x/int(user_input_split[0]),"percent done")
                exec_command(previous_command)
        elif user_input_split[0] == 'sleep' or user_input_split[0] == 's':
            if len(user_input_split) > 1 and user_input_split[1].isdigit():
                time.sleep(int(user_input_split[1]))
            else:
                time.sleep(1)
        elif user_input_split[0] == "changeip":
            if len(user_input_split) > 1:
                ip = user_input_split[1]
            else:
                print(help)
        elif user_input_split[0] == "findroku":
            roku_ips = find_roku()
            print(roku_ips)
            if len(roku_ips) > 0 and len(user_input_split) > 1 and user_input_split[1] == "set":
                ip = roku_ips[0]
                print("set roku ip to",ip)

        if not user_input_split[0].isdigit():
            previous_command = user_input


def input_mode_handler():
    global go, instant_mode, ip
    while go:
        if not instant_mode:
            raw_input = input("> ")
            exec_command(raw_input)
        else:
            time.sleep(1)




def on_press(key):
    global button_dict,toggle_mode_key, instant_mode, ip, go
    if str(key) == toggle_mode_key:
        instant_mode = not instant_mode
        print("switched to",['input','instant'][instant_mode],"mode")
    elif instant_mode:
        if str(key) == "'?'" or str(key)=="'/'":
            print("help:",end="")
            for key in button_dict.keys():
                print(key,'\t',button_dict[key])
            print(f"'?','/'\t help\n{toggle_mode_key}\t toggle input mode")
        else:
            btn=button_dict.get(str(key),None)
            if btn:
                print(btn)
                print(send(f"curl -d '' http://{ip}:8060/keypress/{btn}"))
    return go

def on_release(key):
    pass


def find_roku():
    arp_results = os.popen("arp -a").read()
    try:
        arp_results+=os.popen('py -c "import scapy.all as scapy;scapy.arping(\'192.168.1.1/24\')').read()
    except:
        pass
    try:
        arp_results+=os.popen('network_scanner.py').read()
    except:
        pass
    get_ip = re.compile(r"\d+\.\d+\.\d+\.\d+")
    IPs = [x for x in get_ip.findall(arp_results)]
    # print("\n".join(IPs),"\n\n")

    roku_ips=[]
    threadpool = []
    threads=10
    def workthread():
        while True:
            try:
                IP_to_try = IPs.pop(0)
                # print(IP_to_try)
                requests.get(f"http://{IP_to_try}:8060/query/device-info")
                roku_ips.append(IP_to_try)
                print("roku found!!!",IP_to_try)
            except ConnectionError:
                pass
            except IndexError:
                return 0
            except KeyboardInterrupt:
                return 0
            except:
                pass

    for thr in range(threads):
        threadpool.append(Thread(target=workthread))
        threadpool[thr].start()
    for thr in range(threads):
        threadpool[thr].join()

    return roku_ips


def main():
    global args,ip
    if args.ip:
        ip=args.ip
    if args.command:
        exec_command(args.command)
    else:
        l=Listener(on_press=on_press,on_release=on_release)
        l.start()
        print("welcom to your digital roku controller. press ? or / for help")
        input_mode_handler()
        l.join()

if __name__=="__main__":
    main()
