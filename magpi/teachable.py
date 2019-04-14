#!/usr/bin/env python

import argparse
import sys
import os
import time
from collections import deque, Counter
from functools import partial

os.environ['XDG_RUNTIME_DIR']='/run/user/1000'

from embedding import kNNEmbeddingEngine
from PIL import Image

import gstreamer

def detectPlatform():
  try:
    model_info = open("/sys/firmware/devicetree/base/model").read()
    if 'Raspberry Pi' in model_info:
      print("Detected Raspberry Pi.")
      return "raspberry"
    return "Unknown"
  except:
    print("Could not detect environment.")
    return "unknown"

class UI(object):
  """Abstract UI class. Subclassed by specific board implementations."""
  def __init__(self):
    self._button_state = [False for _ in self._buttons]
    current_time = time.time()
    self._button_state_last_change = [current_time for _ in self._buttons]
    self._debounce_interval = 0.1 # seconds

  def setOnlyLED(self, index):
    for i in range(len(self._LEDs)): self.setLED(i, False)
    if index is not None: self.setLED(index, True)

  def getButtonState(self):
    return [self.isButtonPressed(b) for b in range(len(self._buttons))]

  def getDebouncedButtonState(self):
    t = time.time()
    for i,new in enumerate(self.getButtonState()):
      if not new:
        self._button_state[i] = False
        continue
      old = self._button_state[i]
      if ((t-self._button_state_last_change[i]) >
             self._debounce_interval) and not old:
        self._button_state[i] = True
      else:
        self._button_state[i] = False
      self._button_state_last_change[i] = t
    return self._button_state

  def testButtons(self):
    while True:
      for i in range(5):
        self.setLED(i, self.isButtonPressed(i))
      print('Buttons: ', ' '.join([str(i) for i,v in
          enumerate(self.getButtonState()) if v]))
      time.sleep(0.01)

  def wiggleLEDs(self, reps=3):
    for i in range(reps):
      for i in range(5):
        self.setLED(i, True)
        time.sleep(0.05)
        self.setLED(i, False)

class UI_Raspberry(UI):
  def __init__(self):
    # Only for RPi3: set GPIOs to pulldown
    global rpigpio
    import RPi.GPIO as rpigpio
    rpigpio.setmode(rpigpio.BCM)

    # Layout of GPIOs for Raspberry demo
    self._buttons = [5 , 6 , 13, 19, 26]
    self._LEDs = [25, 12, 16, 20, 21]

    # Initialize them all
    for pin in self._buttons:
      rpigpio.setup(pin, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
    for pin in self._LEDs:
      rpigpio.setup(pin, rpigpio.OUT)
    super(UI_Raspberry, self).__init__()

  def setLED(self, index, state):
    return rpigpio.output(self._LEDs[index],
           rpigpio.LOW if state else rpigpio.HIGH)

  def isButtonPressed(self, index):
    return rpigpio.input(self._buttons[index])

class TeachableMachine(object):
  def __init__(self, model_path, ui, kNN=3, buffer_length=4):
    self._engine = kNNEmbeddingEngine(model_path, kNN)
    self._ui = ui
    self._buffer = deque(maxlen = buffer_length)
    self._kNN = kNN
    self._start_time = time.time()
    self._frame_times = deque(maxlen=40)
    self.clean_shutdown = False

  def classify(self, img, overlay):
    # Classify current image and determine
    emb = self._engine.DetectWithImage(img)
    self._buffer.append(self._engine.kNNEmbedding(emb))
    classification = Counter(self._buffer).most_common(1)[0][0]

    # Interpret user button presses (if any)
    debounced_buttons = self._ui.getDebouncedButtonState()
    for i, b in enumerate(debounced_buttons):
      if not b: continue
      if i == 0: self._engine.clear() # Hitting button 0 resets
      else : self._engine.addEmbedding(emb, i) # otherwise the button # is the class

    # Hitting exactly all 4 class buttons simultaneously quits the program.
    if sum(filter(lambda x:x, debounced_buttons[1:])) == 4 and not debounced_buttons[0]:
      self.clean_shutdown = True
      return True # return True to shut down pipeline

    self._frame_times.append(time.time())
    fps = len(self._frame_times)/float(self._frame_times[-1] - self._frame_times[0] + 0.001)

    # Print/Display results
    self._ui.setOnlyLED(classification)
    classes = ['--', 'Red', 'Orange', 'Green', 'Blue']
    status = 'fps %.1f; #examples: %d; Class % 7s'%(
            fps, self._engine.exampleCount(),
            classes[classification or 0])
    print(status)

    svg = """
    <svg height='320' width='200'>
      <text x='25' y='25' fill='white'>%s</text>
    </svg>
    """
    if overlay:
      overlay.set_property('data', svg%status)
    return False

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='File path of Tflite model.')
    parser.add_argument('--testui', dest='testui', action='store_true',
                        help='Run test of UI. Ctrl-C to abort.')
    args = parser.parse_args()

    # The UI differs a little depending on the system because the GPIOs
    # are a little bit different.
    print('Initialize UI.')
    platform = detectPlatform()
    if platform == 'raspberry': ui = UI_Raspberry()
    else: raise ValueError('Unsupported platform: %s '%platform +
            'This Demo is for Raspberry Pi.')

    ui.wiggleLEDs()
    if args.testui:
        ui.testButtons()
        return

    print('Initialize Model...')
    teachable = TeachableMachine(args.model, ui)

    assert os.path.isfile(args.model)

    print('Start Pipeline.')
    def user_callback(img, overlay):
      return teachable.classify(img, overlay)
    # TODO(mtyka) Refactor this once offial gstreamer.py is
    # programmable and supports rpi. Then get rid of our custom
    # gstreamer.py
    result = gstreamer.run_pipeline(user_callback, platform)

    ui.wiggleLEDs(4)
    return 0 if teachable.clean_shutdown else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))

