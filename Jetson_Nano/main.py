import cv2
import time
import argparse
import numpy as np
import threading
import time
import smbus
import math
import imutils
import sys
import gi
import os
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GObject
from utils.camera import add_camera_args, Camera
from utils.mtcnn import TrtMtcnn
from facemask_model_api import FaceMask
from adafruit_pn532.spi import PN532_SPI
import board
import busio
from digitalio import DigitalInOut
from pyzbar import pyzbar
from Prompts import *
from sqlite import *

STM32_ADDRESS = 0x40
# Open i2c device @/dev/i2c-1, addr 0x40.
bus = smbus.SMBus(1)


def str2bool(v):
  return v.lower() in ("true")

Enabled = [False,False,False,False,False]

with open('Features.txt','r') as file:
    lines = file.readline()
    lines = lines.rstrip('\n')
    temp = lines.split(',')
    print(lines)
    for idx,val in enumerate(temp):
        Enabled[idx] = str2bool(val)
           

WINDOW_NAME = 'CSC'
BBOX_COLOR = (0, 255, 0)  # green
minimum_brightness = 1.5

def parse_args():
    """Parse input arguments."""
    desc = ('Capture and display live camera video, while doing '
            'real-time face detection with TrtMtcnn on Jetson '
            'Nano')
    parser = argparse.ArgumentParser(description=desc)
    parser = add_camera_args(parser)
    parser.add_argument('--minsize', type=int, default=200,
                        help='minsize (in pixels) for detection [40]')
    args = parser.parse_args()
    return args           

args = parse_args()
cam = Camera(args)

if not cam.isOpened():
    raise SystemExit('ERROR: failed to open camera!')



def app_main():
    builder = Gtk.Builder()
    
    builder.add_objects_from_file("Q1.glade", ("Layout", "QuestionLabel","YesLabel","YesSelect","NoLabel","NoSelect"))
    Q1 = builder.get_object("Layout")
    Q1_txt = builder.get_object("QuestionLabel")
    Q1_yes = builder.get_object("YesSelect")
    Q1_no = builder.get_object("NoSelect")
    Q1_yesTxt = builder.get_object("YesLabel")
    Q1_noTxt = builder.get_object("NoLabel")
    Q1_warn = builder.get_object("Warning")
    Q1_begintxt = builder.get_object("Begin")
    Q1_beginSel = builder.get_object("BeginSelect")
    Q1_warn.set_justify(Gtk.Justification.CENTER)
    global progress
    progress = 0
    global Answer
    global NewUID
    global NewUserName
    global VaccinationStatus
    Answer = 0

    QRimage = Gtk.Image()
    QRlabel = Gtk.Label()
    QRfix = Gtk.Fixed()

    QRfix.put(QRimage, 340, 380)
    QRfix.put(QRlabel, 340, 120)

    win = Gtk.Window(default_height=720, default_width=1024)
    win.connect("destroy", Gtk.main_quit)
    win.fullscreen()
    image = Gtk.Image()
    #win.add(label)
    win.add(Q1)

    global curr_obj
    curr_obj = Q1

    global Admin_substate 
    Admin_substate   = 0

    def expose(area, context):
        global progress
        if progress != 0:
            context.set_source_rgb(1, 0, 0)
            context.set_line_width(10)
            context.arc(100, 100, 80, 0, ((progress)/100)*2*math.pi)
            context.stroke()
        else:
            context.set_source_rgb(1, 1, 1)
            context.set_line_width(1)
            context.arc(0, 0, 0, 0, 0.01)
            context.stroke()
            
    Q1_yes.connect("draw", expose)
    Q1_beginSel.connect("draw", expose)
    Q1_no.connect("draw", expose) 
   
    def update_begin(msg):
        global progress
        global Answer        
        data = bus.read_byte(STM32_ADDRESS)
        GLib.idle_add(Q1_warn.set_text,(msg))
        if ((data == 1) or (data == 4) or (data == 9)) and (progress < 100):
            progress = progress + 12
            if progress >= 100:
                Answer = 1
            GLib.idle_add(Q1_beginSel.queue_draw)
        elif (progress < 100):
            progress = 0
            Answer = 0
            GLib.idle_add(Q1_beginSel.queue_draw)

    def update_temperature():
        global progress
        global Answer
        global temperature_buffer        
        data = bus.read_byte(STM32_ADDRESS) * 0.2
        temperature_buffer[int(progress/4)] = data
        #print(temperature_buffer)
        GLib.idle_add(Q1_begintxt.set_markup,("""<span size="28000">""" + str(round(data,1)) + """ C </span>"""))
        progress = progress + 4
		 
        if progress >= 100:
            temp_mean = np.mean(temperature_buffer)
            print(temperature_buffer)
            if temp_mean > 38 :
                Answer = 2
            else :
                Answer = 1
        GLib.idle_add(Q1_beginSel.queue_draw)

    def update_spo2():
        global progress
        global Answer
        global spo2_buffer        
        data = bus.read_byte(STM32_ADDRESS)
        if (data < 101) and (data > 2) :           
            spo2_buffer[int(progress/4)] = data
            #print(temperature_buffer)
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="28000">""" + str(data) + """% </span>"""))
            progress = progress + 4		     
            if progress >= 100:
                spo2_mean = np.mean(spo2_buffer)
                print(spo2_mean)
                if spo2_mean >= 95 :
                    Answer = 1
                else :
                    Answer = 2
        elif progress == 0:
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="28000">Initializing...</span>"""))
        GLib.idle_add(Q1_beginSel.queue_draw)

        

    def update_admin():
        global progress
        global Answer        
        data = bus.read_byte(STM32_ADDRESS)
        if ((data == 1) ) and (progress < 100):
            progress = progress + 12
            if progress >= 100:
                Answer = 1
            GLib.idle_add(Q1_warn.set_text,(""))
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="20000" foreground="#5163bd">Option 1</span>"""))
            GLib.idle_add(Q1_beginSel.queue_draw)
        elif (data == 4):
            progress = progress + 12
            if progress >= 100:
                Answer = 2
            GLib.idle_add(Q1_warn.set_text,(""))
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="20000" foreground="#bd518e">Option 2</span>"""))
            GLib.idle_add(Q1_beginSel.queue_draw)
        elif (data == 9):
            progress = progress + 4
            if progress >= 100:
                Answer = 3
            GLib.idle_add(Q1_warn.set_text,(""))
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="20000" foreground="#bd8c51">Option 3</span>"""))
            GLib.idle_add(Q1_beginSel.queue_draw)
        elif (progress < 100):
            progress = 0
            Answer = 0
            GLib.idle_add(Q1_warn.set_text,"Hover your hand over the sensors to make your decision!")
            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="22000">Selection</span>"""))
            GLib.idle_add(Q1_beginSel.queue_draw)
        

    def update_progess(msg):
        global progress
        global Answer        
        data = bus.read_byte(STM32_ADDRESS)
        GLib.idle_add(Q1_warn.set_text,(msg))
        if (data == 1) and (progress < 100):
            progress = progress + 12
            if progress >= 100:
                Answer = 2
            GLib.idle_add(Q1_yes.queue_draw)
        elif (data == 4) and (progress < 100):
            progress = progress + 12
            if progress >= 100:
                Answer = 1
            GLib.idle_add(Q1_no.queue_draw)
        elif data == 9:
            GLib.idle_add(Q1_warn.set_text,"""Warning! Both Right and Left Sensors are being selected.\nPlease only use one sensor to asnwer the question.""")
        elif (progress < 100):
            progress = 0
            Answer = 0
            GLib.idle_add(Q1_yes.queue_draw)
            GLib.idle_add(Q1_no.queue_draw)
        
        

    def redraw_screen(next):
        global curr_obj
        if curr_obj != next :
            win.remove(curr_obj)       
            win.add(next)
            curr_obj = next
            win.show_all()
        return False

    def reset_prog():
        global progress
        global Answer
        global RFiD_ans
        GLib.idle_add(Q1_txt.set_text,"")
        GLib.idle_add(Q1_yesTxt.set_text,"")
        GLib.idle_add(Q1_noTxt.set_text,"")
        GLib.idle_add(Q1_begintxt.set_text,"")
        GLib.idle_add(Q1_warn.set_text,"")
        progress = 0
        Answer = 0
        RFiD_ans = 0 
        GLib.idle_add(Q1_beginSel.queue_draw)
        GLib.idle_add(Q1_yes.queue_draw)
        GLib.idle_add(Q1_no.queue_draw)     

        
    def Adjust_Brightness(img):
        cols, rows, x = img.shape
        brightness = np.sum(img) / (255 * cols * rows)
        ratio = brightness / minimum_brightness
        if ratio < 1:
            img = cv2.convertScaleAbs(img, alpha = (1 / ratio), beta = 0)                                   
        return img
                
                

    def GUIWorkerThread():     
        run = True
        mtcnn = TrtMtcnn()
        FaceMaskObj = FaceMask('face_mask_detection_model_TFTRT_FP16')
        myROICnt = 0
        confidence_buffer = np.zeros(30)
        conf_cnt = 0
        prog_bar = 0
        pause = False
        global Answer
        global progress
        global state 
        global state_change
        global RFiD_ans
        global NewUID
        RFiD_ans = 0
        state = 0 
        state_change = True
        q_num = 0
        global tracker
        tracker = cv2.TrackerMedianFlow_create()
        b_track = False
        global Admin_substate
        global get_user
        global temperature_buffer
        temperature_buffer = np.zeros(25) 
        Admin_substate   = 0
        temperature_start = False

        global spo2_buffer
        spo2_buffer = np.zeros(25) 
        spo2_start = False
        sanitize = False
        Vaccinated_User = False
        no_track = True
        while True:
            if state == 0:
                if Enabled[0]:
                    if state_change:
                        GLib.idle_add(redraw_screen,Q1)
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(RFIDPrompt))
                        state_change = False
                        Vaccinated_User = False

               
                    time.sleep(0.1)
                    if RFiD_ans == 1:
                        RFiD_ans = 0
                        state = 1
                        state_change = True
                        GLib.idle_add(Q1_txt.set_markup,(CardSuccessPrompt + "Welcome: <b>" + str(get_user[2]) + "\nYou are " + str(get_user[3]) + "</b>"))
                        time.sleep(2)
                        if (get_user[3] == "Vaccinated"):
                            Vaccinated_User = True
                        else :
                            Vaccinated_User = False
                    elif RFiD_ans == 2 :
                        RFiD_ans = 0
                        state = 0
                        state_change = True 
                        GLib.idle_add(Q1_txt.set_markup,(CardFailPrompt))
                        time.sleep(2) 
                else :
                    if state_change:
                        GLib.idle_add(redraw_screen,Q1)
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_begintxt.set_markup,("""<span size="30000">START</span>"""))
                        GLib.idle_add(Q1_txt.set_markup,(FirstPrompt))
                        state_change = False
                        bus.write_byte(STM32_ADDRESS, 0x03)
                        Vaccinated_User = False
                    
                    update_begin(start_screening_msg) 
                    time.sleep(0.1)
                    if Answer == 1:
                        state = 1
                        state_change = True                      

            elif state == 1:
                if Enabled[1]:
                    if state_change:
                        GLib.idle_add(redraw_screen,image)
                        GLib.idle_add(image.set_from_file,'./Face_Mask.jpg')
                        time.sleep(5)
                        state_change = False
                        s = np.zeros(30)
                        conf_cnt = 0
                        prog_bar = 0
                        old_dets = np.array([[1, 1, 2, 2, 0]])
                        confidence_buffer = np.zeros(30)
                        NotDetected = False
                        myROICnt = 6
                        Detected = False
                        Face_was_detected = False
                        print("Face Mask Detection State change")
                    
                    img = cam.read()
                    if img is not None:
                        #img = Adjust_Brightness(img)                                      
                        dets, landmarks = mtcnn.detect(img, minsize=300)
                        cv2.rectangle(img, (30, 0), (1230, 25), (0, 0, 0), -1)
                        if dets.any():
                            if not Face_was_detected:
                                confidence_buffer = np.zeros(30)
                                conf_cnt = 0
                                prog_bar = 0
                                Face_was_detected = True                            
                            bbox = (dets[0][0], dets[0][1], dets[0][2]-dets[0][0], dets[0][3]-dets[0][1])
                            tracker = cv2.TrackerMedianFlow_create()
                            tracker.init(img, bbox)
                            myROICnt = 0
                            img, confidence, class_id = FaceMaskObj.detect(roi=bbox,image=img)
                            if (class_id) and (confidence > 0.8):
                                confidence_buffer[conf_cnt] = confidence
                                conf_cnt = conf_cnt + 1
                                prog_bar = prog_bar + 40
                                
                            else:
                                confidence_buffer[conf_cnt] = (1 - confidence)
                                conf_cnt = conf_cnt + 1
                                prog_bar = prog_bar + 40
                        else :
                            b_track, bbox2 = tracker.update(img)
                            if b_track:
                                img, confidence, class_id = FaceMaskObj.detect(roi=bbox2,image=img)
                                if (class_id) and (confidence > 0.8):
                                    confidence_buffer[conf_cnt] = confidence
                                    conf_cnt = conf_cnt + 1
                                    prog_bar = prog_bar + 40
                                    
                                else:
                                    confidence_buffer[conf_cnt] = 1 - confidence
                                    conf_cnt = conf_cnt + 1
                                    prog_bar = prog_bar + 40                       
                            else:
                                if Face_was_detected:
                                    confidence_buffer = np.zeros(30)
                                    conf_cnt = 0
                                    prog_bar = 0
                                    Face_was_detected = False  
                                confidence_buffer[conf_cnt] = 0
                                conf_cnt = conf_cnt + 1
                                prog_bar = prog_bar + 40 
                                cv2.rectangle(img, (325, 370), (900, 410), (0, 0, 0), -1)
                                cv2.putText(img,"WARNING! NO FACE DETECTED",
                                            (330,400),cv2.FONT_HERSHEY_SIMPLEX,
                                            1, (0, 0, 255), 2, cv2.LINE_AA, False)   
                        if (conf_cnt >= 30):
                            conf_cnt = 0
                        cv2.rectangle(img, (30, 0), (prog_bar+30, 25), (0, 255, 255), -1)
                        conf_mean = np.mean(confidence_buffer)
                        if (conf_mean >= 0.9) and (prog_bar >= 1200):
                            Detected = True
                            NotDetected = False
                            cv2.rectangle(img, (410, 70), (870, 110), (0,255, 0), -1)
                            cv2.putText(img, "Mask Successfully Detected",
                                       (420, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                       1, (0, 0, 0), 2, cv2.LINE_AA, False)
                        elif (prog_bar >= 1200):
                            confidence_buffer.fill(0)
                            prog_bar = 0
                            Detected = False
                            NotDetected = True
                            cv2.rectangle(img, (470, 70), (810, 105), (0, 0, 255), -1)
                            cv2.rectangle(img, (30, 100), (1250, 140), (0, 0, 255), -1)
                            cv2.putText(img, "Mask Not Detected!", 
                                       (480, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                        1, (0, 0, 0), 2, cv2.LINE_AA, False)
                            cv2.putText(img, "Please wear your mask correctly over your Nose and Mouth and try again",
                                       (40, 130), cv2.FONT_HERSHEY_SIMPLEX,
                                        1, (0, 0, 0), 2, cv2.LINE_AA, False)
                            
                       
                        h, w, d = img.shape
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_data(img.tostring(),
                                                                GdkPixbuf.Colorspace.RGB, 
                                                                False, 8, w, h, w*d)                
                        GLib.idle_add(image.set_from_pixbuf,pixbuf.copy(),priority=GLib.PRIORITY_HIGH)
                        if NotDetected:
                            state = 0
                            state_change = True 
                            time.sleep(4)
                        elif Detected:
                            time.sleep(4) 
                            state = 2
                            state_change = True 
                else:
                    state = 2
                    state_change = True    
            elif state == 2:
                if Enabled[2] and (not Vaccinated_User):
                    if state_change:
                        GLib.idle_add(redraw_screen,Q1)
                        reset_prog()
                        GLib.idle_add(Q1_begintxt.set_markup,("""<span size="30000">START</span>"""))
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.LEFT))
                        GLib.idle_add(Q1_txt.set_markup,(TempStartPrompt))
                        state_change = False 
                        bus.write_byte(STM32_ADDRESS, 0x03)
                        temperature_start = False
                        temperature_buffer = np.zeros(25)
                    time.sleep(0.1)
                    if temperature_start :
                        update_temperature()
                        if Answer == 1:
                            time.sleep(0.5)
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_markup,(TempSuccessPrompt))
                            time.sleep(4)
                            state = 3
                            state_change = True 
                        elif Answer == 2 :
                            time.sleep(0.5)
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_markup,(TempFailPrompt))
                            time.sleep(5)
                            state = 0
                            state_change = True 
                    else:
                        update_begin(start_screening_msg)   
                        if Answer == 1:
                            temperature_start = True
                            Answer = 0
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                            GLib.idle_add(Q1_txt.set_markup,(TempRunPrompt))
                            bus.write_byte(STM32_ADDRESS, 0x01)        
                else:
                    state = 3
                    state_change = True
            elif state == 3:
                if Enabled[3] and (not Vaccinated_User):
                    if state_change:
                        GLib.idle_add(redraw_screen,Q1)
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(SanitizerPrompt))
                        state_change = False 
                        bus.write_byte(STM32_ADDRESS, 0x04)
                        spo2_start = False
                        sanitize = True
                        spo2_buffer = np.zeros(25)
                    time.sleep(0.1)
                    if sanitize and (not spo2_start) :
                        try:
                            data = bus.read_byte(STM32_ADDRESS)
                            print("data=" + str(data))
                        except OSError:
                            print("Read Byte Error")  
                            
                        if data == 1: 
                            sanitize = False
                            reset_prog()
                            GLib.idle_add(Q1_begintxt.set_markup,("""<span size="30000">START</span>"""))
                            GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.LEFT))
                            GLib.idle_add(Q1_txt.set_markup,(Spo2StartPrompt)) 
                            bus.write_byte(STM32_ADDRESS, 0x03)                           
                    elif spo2_start and (not sanitize):
                        update_spo2()
                        if Answer == 1:
                            time.sleep(0.5)
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_markup,(Spo2SuccessPrompt))
                            time.sleep(4)
                            state = 4
                            state_change = True 
                        elif Answer == 2 :
                            time.sleep(0.5)
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_markup,(Spo2FailPrompt))
                            time.sleep(5)
                            state = 0
                            state_change = True 
                    else:
                        update_begin(start_screening_msg)   
                        if Answer == 1:
                            spo2_start = True
                            Answer = 0
                            reset_prog()
                            GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                            GLib.idle_add(Q1_txt.set_markup,(Spo2RunPrompt))
                            bus.write_byte(STM32_ADDRESS, 0x02)        
                else:
                    state = 4
                    state_change = True                          
            elif state == 4:
                if Enabled[4] and (not Vaccinated_User):
                    if state_change:
                        GLib.idle_add(redraw_screen,Q1)
                        reset_prog()
                        GLib.idle_add(Q1_begintxt.set_markup,("""<span size="30000">START</span>"""))
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.LEFT))
                        GLib.idle_add(Q1_txt.set_markup,(SurveyPrompt))
                        state_change = False
                        q_num = 0
                        bus.write_byte(STM32_ADDRESS, 0x03)
                    
                    time.sleep(0.1)
                    if q_num  == 0:                
                        update_begin(start_screening_msg)
                    else:
                        update_progess(YesNoWarn)

                    if Answer == 1:
                        time.sleep(0.5)
                        if (q_num == (len(Questions))):
                            state = 5
                            state_change = True
                            reset_prog()
                        else:
                            GLib.idle_add(Q1_txt.set_markup,(Questions[q_num]))
                            GLib.idle_add(Q1_yesTxt.set_text,("YES"))
                            GLib.idle_add(Q1_noTxt.set_text,("NO"))
                            GLib.idle_add(Q1_begintxt.set_text,(""))
                            q_num = q_num + 1
                            progress = 0
                            Answer = 0
                            time.sleep(0.5)                       
                    elif Answer == 2:
                        reset_prog()
                        GLib.idle_add(Q1_begintxt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,SurveyFailPrompt)
                        time.sleep(4)
                        state = 0
                        state_change = True
                else :
                    state = 5
                    state_change = True
            elif state == 5:
                if state_change:
                    GLib.idle_add(redraw_screen,Q1)
                    reset_prog()
                    if (Vaccinated_User):
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(VaccinatedPrompt))                        
                    else :
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(ScreenSuccessPrompt))
                    bus.write_byte(STM32_ADDRESS, 0x03)  
                    state_change =  False
                time.sleep(0.1)    
                if progress <= 100:
                    progress = progress + 1
                    GLib.idle_add(Q1_beginSel.queue_draw)
                else :
                    state_change = True
                    state = 0
            elif state == 9:
                if state_change:
                    GLib.idle_add(redraw_screen,Q1)
                    reset_prog()
                    Admin_substate  = 0
                    GLib.idle_add(Q1_begintxt.set_justify,(Gtk.Justification.CENTER))
                    GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.LEFT))
                    GLib.idle_add(Q1_txt.set_markup,(AdminPrompt))
                    state_change = False
                    q_num = 0
                    bus.write_byte(STM32_ADDRESS, 0x03)
                
                if Admin_substate == 0 :
                    update_admin()
                    time.sleep(0.1)
                    if Answer == 1:
                        Admin_substate = 1
                        reset_prog()
                        GLib.idle_add(Q1_yesTxt.set_text,("Add"))
                        GLib.idle_add(Q1_noTxt.set_markup,("<small>Remove</small>"))
                        GLib.idle_add(Q1_txt.set_markup,(AddRemoveUserPrompt)) 
                    elif Answer == 2:
                        Answer = 0
                        Admin_substate = 2
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(FeaturesPrompt[0]))
                        GLib.idle_add(Q1_yesTxt.set_text,("YES"))
                        GLib.idle_add(Q1_noTxt.set_text,("NO"))             
                    elif Answer == 3:
                        os.system( "shutdown now -h")
                        GLib.idle_add(Gtk.main_quit)
                elif Admin_substate == 1:
                    update_progess("Hover your hand over the sensors to make your decision!")
                    time.sleep(0.1)
                    if Answer == 1:
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(RemoveUserPrompt))
                        Admin_substate = 12
                    elif Answer == 2:
                        reset_prog()
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(NewUserPrompt))
                        Admin_substate = 11                             
                elif Admin_substate == 11:
                    time.sleep(0.1)
                    if (RFiD_ans == 1) :
                        RFiD_ans = 0
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(NewUserPrompt2))
                        Admin_substate = 111
                        time.sleep(2)
                        GLib.idle_add(redraw_screen,QRfix)
                        prog_bar = 0
                    elif (RFiD_ans == 2) :
                        RFiD_ans = 0
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(NewUserPrompt3))
                        state_change = True
                        time.sleep(2)
                elif Admin_substate == 111:
                        # find the barcodes in the image and decode each of the barcodes
                        img = cam.read()
                        img = imutils.resize(img, width=600)
                        barcodes = pyzbar.decode(img)
                        #print (barcodes)
                        # loop over the detected barcodes
                        cv2.rectangle(img, (30, 0), (570, 8), (0, 0, 0), -1)
                        if barcodes:
                            # extract the bounding box location of the barcode and draw the
                            # bounding box surrounding the barcode on the image
                            (x, y, w, h) = barcodes[0].rect
                            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 2)
                            # the barcode data is a bytes object so if we want to draw it on
                            # our output image we need to convert it to a string first
                            barcodeData = barcodes[0].data.decode("utf-8")
                            barcodeType = barcodes[0].type
                            # draw the barcode data and barcode type on the image
                            text = "{} ({})".format(barcodeData, barcodeType)
                            cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2,cv2.LINE_AA,False)
                            data = barcodeData.split(",")
                            if len(data) > 1:
                                Vaccinated = data[1].strip()
                                if (Vaccinated == "Vaccinated") or (Vaccinated == "Not Vaccinated") :
                                    GLib.idle_add(QRlabel.set_markup,"<span size='20000'><span weight='bold' foreground='green'>QRCode Detected!</span>\n\nFull Name: <b>" + data[0] + "</b>\nVaccination Status: <b>" + Vaccinated + "</b> \n\n Please hold steady for confirmation! </span>")
                                    if prog_bar < 570:
                                        prog_bar = prog_bar + 20
                                    else :
                                        prog_bar = 570
                                        JoinedUID = ' '.join(NewUID)
                                        conn = create_connection(r"Users.db")
                                        with conn:
                                            user = (JoinedUID, data[0].strip(), Vaccinated,'2021-03-15 11:50:23.040258');
                                            project_id = create_user(conn, user)
                                        conn.close()
                                        GLib.idle_add(QRlabel.set_markup,"<span size='20000'><span weight='bold' foreground='green'>QRCode Detected!</span>\n\nFull Name: <b>" + data[0] + "</b>\nVaccination Status: <b>" + Vaccinated + "</b> \n\n New User Successfully Registered! </span>")
                                        time.sleep(3)
                                        state_change = True
                                    cv2.rectangle(img, (30, 0), (prog_bar, 8), (0, 255, 0), -1)
                                else :
                                    GLib.idle_add(QRlabel.set_markup,"<span size='20000'><span weight='bold' foreground='red'>QRCode Error Detected!</span>\n\nFull Name: <b>" + data[0] + "</b>\nVaccination Status:<span foreground='red'><b>" + Vaccinated + "</b></span>\n\nPlease make sure that Vaccination status is spelled correctly!</span>")
                        else:
                            prog_bar = 30
                            GLib.idle_add(QRlabel.set_markup,"<span font_family='Open Sans' size='20000'><span weight='bold' foreground='red'>QRCode Not Detected!</span>\nPlease hold up a QRCode to the camera in <i>utf-8 encoding</i> which\ndetails the user's <b>Full Name</b> and their <b>Vaccination status</b>.\nThe encoded text should be in the following format:\n(<i>Full Name</i>), (<i>Vaccination Status</i>) \nExample 1: 'John Doe, Vaccinated' \nExample 2: 'Jane Doe, Not Vaccinated'</span>")

                            
                        height, width, d = img.shape
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_data(img.tostring(), GdkPixbuf.Colorspace.RGB, False, 8, width, height,width*d)
                        GLib.idle_add(QRimage.set_from_pixbuf,pixbuf.copy())
                elif Admin_substate == 12:
                    if (RFiD_ans == 1) :
                        RFiD_ans = 0
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(RemoveUserPrompt2))
                        state_change = True
                        time.sleep(3)    
                    elif (RFiD_ans == 2) :
                        RFiD_ans = 0
                        GLib.idle_add(Q1_txt.set_justify,(Gtk.Justification.CENTER))
                        GLib.idle_add(Q1_txt.set_markup,(RemoveUserPrompt3))
                        state_change = True
                        time.sleep(3)
                elif Admin_substate == 2:
                    update_progess(YesNoWarn)
                    time.sleep(0.1)
                    if Answer == 2:                        
                        Enabled[q_num] = True
                        q_num = q_num + 1
                    elif Answer == 1:
                        Enabled[q_num] = False
                        q_num = q_num + 1
                    print("Im in substate 2: " + str(Answer) + " " + str(q_num))    
                    if (q_num == (len(FeaturesPrompt))):
                        with open('Features.txt','w') as file:
                            temp_str = (str(Enabled)).replace('[','').replace(']','').replace(' ','')
                            file.write(temp_str)        
                        state_change = True
                    elif (Answer != 0):
                        time.sleep(0.5)
                        reset_prog() 
                        GLib.idle_add(Q1_txt.set_markup,(FeaturesPrompt[q_num]))
                        GLib.idle_add(Q1_yesTxt.set_text,("YES"))
                        GLib.idle_add(Q1_noTxt.set_text,("NO"))   
                        progress = 0
                        Answer = 0

                    
                                                                 
                            
    def MyRFIDThread() :
        # SPI connection:
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        irq_pin = DigitalInOut(board.D17)
        cs_pin = DigitalInOut(board.D5)
        pn532 = PN532_SPI(spi, cs_pin, debug=False, irq=irq_pin)
        #ic, ver, rev, support = pn532.firmware_version
        # Configure PN532 to communicate with MiFare cards
        pn532.SAM_configuration()
        pn532.listen_for_passive_target()
        admin = ['0x87', '0x7c', '0xc9', '0xa6']
        newID = ['','','','']
        global state_change
        global state
        global RFiD_ans
        global Admin_substate
        global NewUID
        global get_user 
        RFiD_ans = 0
        counter = 0
        UserFound = False
        while True:
            # Check if a card is available to read
            if (irq_pin.value == 0) and (RFiD_ans == 0):
                uid = pn532.get_passive_target()
                if uid is not None:
                    for idx, val in enumerate(uid):
                        newID[idx] = hex(val)
                    conn = create_connection(r"Users.db")
                    with conn:
                        get_user = search_all_users(conn,' '.join(newID))
                        if get_user is not None:
                            UserFound = True
                        else:
                            UserFound = False
                    conn.close()

                if (newID == admin) and (state != 9):
                    print("Admin is detected: " + str(newID))
                    state = 9
                    state_change = True
                    RFiD_ans = 3
                    time.sleep(1)
                elif (newID == admin) and (state == 9):
                    state = 0
                    print("Admin is detected in state 9: "+ str(newID))
                    state_change = True
                    RFiD_ans = 3
                    time.sleep(1)                    				
                elif (not UserFound) and (state == 9) and (Admin_substate == 11):
                    RFiD_ans = 1
                    print("Saving user with ID:" + str(newID))
                    NewUID = newID
                    time.sleep(1)
                elif (UserFound) and (state == 9) and (Admin_substate == 11):
                    RFiD_ans = 2
                    print("Couldn't save user with ID:" + str(newID))
                    time.sleep(1)
                elif (UserFound) and (state == 9) and (Admin_substate == 12):
                    conn = create_connection(r"Users.db")
                    with conn:
                        delete_user(conn,' '.join(newID))
                    conn.close()
                    RFiD_ans = 1
                    print("Removing user with ID:" + str(newID))
                    time.sleep(1)
                elif (not UserFound) and (state == 9) and (Admin_substate == 12):
                    RFiD_ans = 2
                    print("Couldn't Remove user with ID:" + str(newID))
                    time.sleep(3)
                elif Enabled[0] and (UserFound) and (state == 0):
                    RFiD_ans = 1
                    print("User detected: " + str(newID))
                    time.sleep(1)
                elif Enabled[0] and (not UserFound) and (state == 0):
                    RFiD_ans = 2
                    print("User not detected: " + str(newID))
                    time.sleep(1)	
                pn532.listen_for_passive_target()
            else :
                UserFound = False
 
            time.sleep(0.1)

    win.show_all()
    
    thread = threading.Thread(target = GUIWorkerThread)
    thread.daemon=True
    thread.start()

    rfid_thread = threading.Thread(target=MyRFIDThread)
    rfid_thread.daemon=True 
    rfid_thread.start()



def main():
    
    bus.write_byte(STM32_ADDRESS, 0x03)
    app_main()
    Gtk.main()
    cam.release()
    
    


if __name__ == '__main__':
    main()
