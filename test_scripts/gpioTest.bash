#!/bin/bash

# Continuously monitor GPIO17 on Raspberry Pi 5 (BCM numbering)

CHIP="gpiochip0"
PIN="17"

while true; do
    VALUE=$(gpioget $CHIP $PIN)
    echo "$(date '+%H:%M:%S') GPIO$PIN = $VALUE"
    sleep 0.1
done
