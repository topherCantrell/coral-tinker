#!/usr/bin/env python

from periphery import GPIO, PWM
import time

LEDs = [GPIO(25, 'out'), 
        GPIO(12, 'out'), 
        GPIO(16, 'out'), 
        GPIO(20, 'out'), 
        GPIO(21, 'out')]   

for led in LEDs:
  print(led)


while True:
  for led in LEDs: led.write(True)
  print("ON")
  time.sleep(0.35)
  for led in LEDs: led.write(False)
  print("OFF")
  time.sleep(0.20)

