#!/user/bin/new/python3

import pygame
import can
import os
import subprocess
import cv2
import time
import threading
import images
import guages
import json
from statistics import mean
import time
from picamera2 import Picamera2
from time import sleep
#from rtc_lib import RTC_DS3231

# Initialize Pygame
pygame.init()
pygame.mouse.set_visible(False)

# Camera setup
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (800, 480)}))
camera_on = False
camera_running = False
latest_frame = None

# Set up the display
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Car Data Dashboard")

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_NEON = (145, 213, 89) #FOR Digital Hex #'s

# Define font for text display
font = pygame.font.SysFont("Arial", 30)
digi_font = pygame.font.SysFont("/home/qst/Desktop/Digital-Tractor-Dash/fonts/DSEG7Classic-Bold.ttf", 30)

# Setup CAN Bus interface
bus = can.interface.Bus(channel='can0', interface='socketcan')

# Variables to store parameter values - note - Take into account the offset when converting into output values.
#taken from j1939 Communication for the PCS automatic Transmission Controller
#the scale is called the resolution on the document
rpm = 0
rpm_offset = 0
rpm_scale = .125 *3600/8100
rpm_avg = []
throttle_data = 0
throttle_percent = 0
load_percent = 0
throttle_offset = 0
throttle_scale = 4/10#percent
coolant_temp = 0
coolant_offset = -40
coolant_scale = 1
oil_pressure = 0
oil_pressure_offset = 0
oil_pressure_scale = .1
battery_voltage = 0
battery_offset = 0
battery_scale = .1
oil_lamp_indicator = 00
malfunction_lamp = 00


# possible options to check
poss = []
# Function to read J1939 data and update variables
def listen_for_j1939():
    global rpm, rpm_photo, rpm_avg, throttle_percent, load_percent, coolant_temp, oil_pressure, battery_voltage, oil_lamp_indicator, malfunction_lamp
    while True:
        os.system('sudo ip link set can0 type can bitrate 250000')
        os.system('sudo ifconfig can0 up')

        can0 = can.interface.Bus(channel = 'can0', interface = 'socketcan')# socketcan_native

        while True:
            #msg = can.Message(arbitration_id=0x123, data=[0, 1, 2, 3, 4, 5, 6, 7], is_extended_id=False)
            message = can0.recv(10.0)
            if message:
                #Add if block to only run code if message is engine ID
                pgn_message = (message.arbitration_id >> 8) & 0x03FFFF #bits 8 to 23 form the pgn
                pgn_hex = f"0x{pgn_message:04x}" #convert back into hex for testing
                #print (message)
                #print (message.arbitration_id)
                #print (pgn_message)
                if message not in poss:
                    poss.append(message)
            
                #RPM
                if pgn_message == 61444:
                    rpm_data = message.data
                    rpm = int(rpm_data[3]<<8) + int(rpm_data[4]) #rpm is bytes 4 & 3 of message.data - converting to decimal - may have to reverse these values
                    #rpm = (rpm * rpm_scale) + rpm_offset#multiply by the scale
                    rpm_avg.append(rpm)
                    if(len(rpm_avg) == 51):
                       rpm_avg = rpm_avg[1:]
                       rpm = mean(rpm_avg)/8#divide added from email here4r9
                    else:
                        rpm = 0
                    rpm = int(round(rpm, -2)) # Round to the nearest hundreth (for the photos)
                    if(rpm>4000):
                        rpm = 4000
                        # Throttle percent at specific speed
                        
                elif pgn_message == 61443:
                     throttle_data = message.data
                     throttle_percent = int(throttle_data[1])  # Throttle percent might be in the first byte
                     throttle_percent = (throttle_percent * throttle_scale) + throttle_offset
                     throttle_percent = int(round(throttle_percent/5))
                     load_percent = int(throttle_data[2])
                     load_percent = load_percent*throttle_scale
                     load_percent = int(round(load_percent))

                # Coolant temperature (e.g., PGN 0x18F00401)
                elif pgn_message == 65038:
                    coolant_data = message.data
                    coolant_temp = int(coolant_data[0], 16) # Coolant temperature offset by 40 for the J1939 standard
                    coolant_temp = (coolant_temp * coolant_scale) + coolant_offset
                    coolant_temp = int(round(coolant_temp))

                # Oil pressure (e.g., PGN 0x18F00402)
                elif pgn_message == 65039:
                    oil_pressure_data = message.data
                    oil_pressure = int(oil_pressure_data[3], 16)  # Oil pressure might be in the first byte
                    oil_pressure = (oil_pressure * oil_pressure_scale) + oil_pressure_offset

                # Battery voltage (e.g., PGN 0x18F00403)
                elif pgn_message == 65047: # may have to check the spn
                    battery_data = message.data
                    battery_voltage = int(battery_data[4] + battery_data[5], 16) #may be 6 and 7
                    battery_voltage = (battery_voltage * battery_voltage_scale) + battery_voltage_offset
                    
                elif pgn_message == 65226:
                    #OIL PRESSURE LAMP AND CHECK ENGINE LAMP
                    lamp_data = message.data
                    lamp_data = lamp_data[1] #may be 2
                    oil_lamp_indicator = bin(lamp_data)[5:7]
                
                    #Engine error light
                    lamp_data = message.data
                    lamp_data = lamp_data[0]
                    malfunction_lamp = bin(lamp_data)[0:2]

            #time.sleep(0.001)  # Optional delay to prevent overloading the CPU- Limits message interactions D0nt use it
        os.system('sudo ifconfig can0 down')

# Function to display the data on screen
def display_data():
    
    #RPM & throttle
    screen.blit(pygame.image.load('/home/qst/Desktop/Digital-Tractor-Dash/images/background.png'), (0, 0))  # Fill screen with black background
    #print(f"throttle raw value:'{throttle_percent}', int:{int(throttle_percent)}, {throttle_percent:02.0f}")
    screen.blit(pygame.image.load(f'/home/qst/Desktop/Digital-Tractor-Dash/guages/aux{int(throttle_percent)}.png'), (668, 0)) #throttle percentage
    screen.blit(pygame.image.load(f'/home/qst/Desktop/Digital-Tractor-Dash/images/rpm/RPM {rpm:03.0f}.png'), (0, 0)) #throttle percentag
    screen.blit(pygame.image.load(f'/home/qst/Desktop/Digital-Tractor-Dash/guages/aux{int(load_percent)}.png'), (500, 0))
    screen.blit(pygame.image.load(f'/home/qst/Desktop/Digital-Tractor-Dash/guages/aux{int(coolant_temp)}.png'), (582, 0))
    
     #indicator lights - change next day with the aux lights.
    #left light
    screen.blit(pygame.image.load('/home/qst/Desktop/Digital-Tractor-Dash/guages/aux0.png'), (-5, 0))
 
    #right light
    screen.blit(pygame.image.load('/home/qst/Desktop/Digital-Tractor-Dash/guages/aux0.png'), (72, 0))

     
     #Problem idicators
    if battery_voltage < 10: #test when Engine on
        screen.blit(pygame.image.load('/home/qst/Desktop/Digital-Tractor-Dash/indicators/voltageOn.png'), (0, 0))
         
    #Oil Lamp
    lamp_state = '/home/qst/Desktop/Digital-Tractor-Dash/indicators/lowoilOff.png' if oil_lamp_indicator == 00 else '/home/qst/Desktop/Digital-Tractor-Dash/indicators/lowoilOn.png' #malfunction indicator lamp
    screen.blit(pygame.image.load(lamp_state), (0, 0))
       
    #malfunction lamp
    lamp_state = '/home/qst/Desktop/Digital-Tractor-Dash/indicators/engineOff.png' if oil_lamp_indicator == 00 else '/home/qst/Desktop/Digital-Tractor-Dash/indicators/engineOn.png' #malfunction indicator lamp
    screen.blit(pygame.image.load(lamp_state), (0, 0))
#     screen.blit(pygame.image.load(f'guages/aux{coolant_temp:02d}.png'), (582, 0))
#     screen.blit(pygame.image.load(f'guages/aux{coolant_temp:02d}.png'), (582, 0))

    pygame.display.flip()  # Update the screen with new data


def kill_camera():
    try:
        offenders = ['libcamera-still', 'libcamera-vid', 'libcamera-hello', 'picamera2']
        for name in offenders:
            subprocess.run(['pkill', '-f', name], check=False)
    except Exception as e:
        print("Error killing camera users")

# Camera thread
def camera_thread():
    global latest_frame
    picam2.start()
    while True:
        if camera_on:
            frame = picam2.capture_array()[..., ::-1]
            latest_frame = frame
        else:
            latest_frame = None
        time.sleep(0.03)
# Main loop
running = True
clock = pygame.time.Clock()

# Start the CAN listener in a separate thread to avoid blocking the main loop

listener_thread = threading.Thread(target=listen_for_j1939)
listener_thread.daemon = True  # Set as daemon so it exits when the main program exits
listener_thread.start()

        
# Kill other camera users and start our own Thread
kill_camera()
cam_thread = threading.Thread(target=camera_thread)
cam_thread.daemon = True
cam_thread.start()

# Main loop (adjusted to toggle camera on 'k' press)
screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if x < 50 and y < 30:
                running = False
            else:
                camera_on = not camera_on  # Toggle camera feed

    if latest_frame is not None:
        surf = pygame.surfarray.make_surface(latest_frame.swapaxes(0, 1))
        rotated = pygame.transform.rotate(surf, 270)
        scaled = pygame.transform.smoothscale(rotated, (800, 480))
        screen.blit(scaled, (0, 0))
    else:
        display_data()

    pygame.display.flip()
    time.sleep(0.01)

pygame.quit()

