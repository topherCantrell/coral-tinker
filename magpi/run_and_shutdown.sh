#!/bin/bash

python3.5 teachable.py --model=mobilenet_quant_v1_224_headless_edgetpu.tflite && sudo shutdown -h now
