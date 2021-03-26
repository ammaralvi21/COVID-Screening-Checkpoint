#!/bin/bash
sudo jetson_clocks --fan
sudo systemctl restart nvargus-daemon.service
cd /home/capstone/Capstone_Proj/Portable-COVID-19-Screening-Device/Jetson_Nano
sudo nice -n -10 python3 main.py --onboard 1
