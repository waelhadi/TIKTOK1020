import pyfiglet
from termcolor import colored

hakm_logo = pyfiglet.figlet_format("NASR")
print(colored(hakm_logo, "cyan"))
print(colored("معرّف المطوّر: @NASR101", "cyan"))


clear()
from termcolor import colored
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

print(colored("[1]  سحب بروكسي قوي", "cyan"))
print(colored("[2]  سحب بروكسي ضعيف", "cyan"))
print(colored("[3]  أبدء البلاغ", "cyan"))

Get_aobsh = input(colored("[×] اختار : ", "cyan"))
clear()
