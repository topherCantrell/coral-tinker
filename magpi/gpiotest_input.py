#!/usr/bin/env python

from periphery import GPIO, PWM
import time

import RPi.GPIO as rpigpio
rpigpio.setmode(rpigpio.BCM)
rpigpio.setup(26, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
rpigpio.setup(19, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
rpigpio.setup(13, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
rpigpio.setup(6 , rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
rpigpio.setup(5 , rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)

INPs = [
  GPIO(26, 'in'),   
  GPIO(19, 'in'),   
  GPIO(13, 'in'),   
  GPIO(6 , 'in'),   
  GPIO(5 , 'in') 
]   

for inp in INPs:
  print(inp)

while True:
  print([inp.read() for inp in INPs])
  time.sleep(0.05)

