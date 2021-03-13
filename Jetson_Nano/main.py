import time
import argparse
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GObject
import cv2
from utils.camera import add_camera_args, Camera
from utils.display import open_window, set_display, show_fps
from utils.mtcnn import TrtMtcnn
from facemask_model_api import FaceMask
import numpy as np
import threading
import time
import ctypes
import smbus
import math
from adafruit_pn532.spi import PN532_SPI
import board
import busio
from digitalio import DigitalInOut
STM32_ADDRESS = 0x40
# Open i2c device @/dev/i2c-1, addr 0x40.
bus = smbus.SMBus(1)

Questions = ("""                    <i>1/5</i>
Do you have any of the following <b>symptoms</b> which are new or worsened 
if associated with allergies, chronic or pre-existing conditions?

 - Fever (temperature ≥ 38.0 Celsius)
 - cough
 - shortness of breath
 - difficulty breathing
 - sore throat
 - runny nose
""", """                            <i>2/5</i>

Have you returned to Canada from outside the country <b>(including USA)</b> 
in the <b>past 14 days</b>?
""","""                             <i>3/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>

Did you have close contact with a person who has a probable or 
confirmed case of COVID-19?
""","""                             <i>4/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>

Did you have close contact with a person who had an acute respiratory 
illness that started within <b>14 days</b> of their close contact to someone 
with a probable or confirmed case of COVID-19?
""","""                             <i>5/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>

Did you have close contact with a person who had an acute respiratory 
illness who returned from travel outside of Canada in the <b>14 days</b> 
before they became sick?
""")

SurveyPrompt = """
We will ask a series of daily screening Questions to protect from
exposure during the COVID-19 pandemic and provide a safe environment

<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
SpO2Prompt = """
<b>We will now take your SpO2 reading.</b> 
Place your right finger underneath the device where the arrow points to.
Make sure to cover the sensor with the entirety of your finger.

<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
TemperaturePrompt = """
We will ask a series of daily screening Questions to protect from
exposure during the COVID-19 pandemic and provide a safe environment

<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
FirstPrompt = """
<big><b>COVID SCREENING CHECKPOINT</b></big>
"""
start_screening_msg = """Hover your hand on any of the two sensors to start screening!\r
Keep your hand very close to the sensor and steady until the selection is confirmed.\r"""

start_survey_msg = """Hover your hand on any of the two sensors to begin the survey!\r
Keep your hand very close to the sensor and steady until the selection is confirmed.\r"""

Enabled = (False,True, False, False, True)

WINDOW_NAME = 'TrtMtcnnDemo'
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
    Answer = 0
   

    win = Gtk.Window(default_height=720, default_width=1024)
    win.connect("destroy", Gtk.main_quit)
    win.fullscreen()
    image = Gtk.Image()
    #win.add(label)
    win.add(image)
    global curr_obj
    curr_obj = image

    def expose(area, context):
        global progress
        if progress != 0:   
            context.set_source_rgb(1, 0, 0)
            context.set_line_width(10)
            context.arc(100, 100, 80, 0, ((progress*4)/100)*2*math.pi)
            context.stroke()
            
    Q1_yes.connect("draw", expose)
    Q1_beginSel.connect("draw", expose)
    Q1_no.connect("draw", expose) 
   
    def update_begin(msg):
        global progress
        global Answer        
        data = bus.read_byte(STM32_ADDRESS)
        Q1_warn.set_text(msg)
        if ((data == 1) or (data == 4) or (data == 9)) and (progress < 25):
            progress = progress + 3
            if progress >= 25:
                Answer = 1
            Q1_beginSel.queue_draw()
        elif (progress < 25):
            progress = 0
            Answer = 0
            Q1_beginSel.queue_draw()
        return False

    def update_progess():
        global progress
        global Answer        
        data = bus.read_byte(STM32_ADDRESS)
        Q1_warn.set_text("""Hover your hand over the Right Sensor for "Yes" and Left Sensor for "No".\r
Keep your hand very close to the sensor and steady until the selection is confirmed.\r""")
        if (data == 1) and (progress < 25):
            progress = progress + 3
            if progress >= 25:
                Answer = 2
            Q1_yes.queue_draw()
        elif (data == 4) and (progress < 25):
            progress = progress + 3
            if progress >= 25:
                Answer = 1
            Q1_no.queue_draw()
        elif data == 9:
            Q1_warn.set_text("""Warning! Both Right (Yes) and Left (No) Sensors are being selected.
 Please only use one sensor to asnwer the question.""")
        elif (progress < 25):
            progress = 0
            Answer = 0
            Q1_yes.queue_draw()
            Q1_no.queue_draw()
        
        return False

    def redraw_screen(next):
        global curr_obj
        win.remove(curr_obj)       
        win.add(next)
        curr_obj = next
        win.show_all()
        return False


    def Adjust_Brightness(img):
        cols, rows, x = img.shape
        brightness = np.sum(img) / (255 * cols * rows)
        ratio = brightness / minimum_brightness
        if ratio < 1:
            img = cv2.convertScaleAbs(img, alpha = (1 / ratio), beta = 0)                                   
        return img
                
                

    def MyThread():     
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
        state = 0
        state_change = True
        q_num = 0
        tracker = cv2.TrackerMedianFlow_create()
        b_track = False
        while True:
            if state == 0:
                if state_change:
                    GLib.idle_add(redraw_screen,Q1)
                    Q1_yesTxt.set_text("")
                    Q1_noTxt.set_text("")
                    Q1_begintxt.set_text("START")
                    Q1_txt.set_markup(FirstPrompt)
                    state_change = False
                    progress = 0
                    Answer = 0                    

                GLib.idle_add(update_begin,start_screening_msg) 
                time.sleep(0.1)
                if Answer == 1:
                    state = 1
                    print ("changing state")
                    state_change = True 
                      

            elif state == 1:
                if Enabled[1]:
                    if state_change:
                        GLib.idle_add(redraw_screen,image)
                        state_change = False
                        s = np.zeros(30)
                        conf_cnt = 0
                        prog_bar = 0
                        old_dets = np.array([[1, 1, 2, 2, 0]])
                        confidence_buffer = np.zeros(30)
                        pause = False
                        myROICnt = 6
                        run = True

                    img = cam.read()
                    
                    print("--------------------------------")                    
                    if img is not None:
                        img = Adjust_Brightness(img)                                         
                        dets, landmarks = mtcnn.detect(img, minsize=200)
                        cv2.rectangle(img, (30, 0), (1230, 25), (0, 0, 0), -1)
                        if dets.any():
                            bbox = (dets[0][0], dets[0][1], dets[0][2]-dets[0][0], dets[0][3]-dets[0][1])
                            tracker = cv2.TrackerMedianFlow_create()
                            ok = tracker.init(img, bbox)
                            print("track_init:" + str(ok))
                            print(bbox)
                            myROICnt = 0
                            img, confidence, class_id = FaceMaskObj.detect(roi=bbox,image=img)
                            if (class_id) and (confidence > 0.8):
                                confidence_buffer[conf_cnt] = confidence
                                conf_cnt = conf_cnt + 1
                                prog_bar = prog_bar + 40
                                
                            else:
                                confidence_buffer.fill(0.0)
                                prog_bar = 0
                        else :
                            b_track, bbox2 = tracker.update(img)
                            print("tracking......")
                            print(b_track)
                            print(bbox2)
                            if b_track:
                                img, confidence, class_id = FaceMaskObj.detect(roi=bbox2,image=img)
                                print(class_id) 
                                if (class_id) and (confidence > 0.8):
                                    confidence_buffer[conf_cnt] = confidence
                                    conf_cnt = conf_cnt + 1
                                    prog_bar = prog_bar + 40
                                    
                                else:
                                    confidence_buffer.fill(0.0)
                                    prog_bar = 0                            
                            else:
                                confidence_buffer.fill(0.0)
                                prog_bar = 0
                            
                        if (conf_cnt >= 30):
                            conf_cnt = 0
                        cv2.rectangle(img, (30, 0), (prog_bar+30, 25), (102, 179, 255), -1)
                        conf_mean = np.mean(confidence_buffer)
                        if (conf_mean >= 0.9) and (prog_bar >= 1200):
                            run = False
                            pause = True
                            cv2.rectangle(img, (410, 70), (870, 110), (255,255, 255), -1)
                            cv2.putText(img, "Mask Successfully Detected", (420, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA, False)
                        elif (prog_bar >= 1200):
                            confidence_buffer.fill(0.0)
                            prog_bar = 0
                            pause = True
                            cv2.rectangle(img, (470, 70), (810, 105), (0, 0, 255), -1)
                            cv2.rectangle(img, (30, 100), (1250, 140), (0, 0, 255), -1)
                            cv2.putText(img, "Mask Not Detected!", (480, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA, False)
                            cv2.putText(img, "Please wear your mask correctly over your Nose and Mouth and try again", (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA, False)
                            
                       
                        h, w, d = img.shape
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        pixbuf = GdkPixbuf.Pixbuf.new_from_data(img.tostring(), GdkPixbuf.Colorspace.RGB, False, 8, w, h, w*d)                

                        GLib.idle_add(image.set_from_pixbuf,pixbuf.copy())
                        if pause:
                            pause = False 
                            time.sleep(5)
                        if run == False: 
                            state = 2
                            print ("changing state")
                            state_change = True 
                else:
                    state = 2
                    state_change = True    
            elif state == 2:
                if Enabled[2]:
                    if state_change:
                        print("Was Here")
                        GLib.idle_add(redraw_screen,Q1)
                        Q1_yesTxt.set_text("")
                        Q1_noTxt.set_text("")
                        Q1_begintxt.set_text("START")
                        Q1_txt.set_markup(SurveyPrompt)
                        state_change = False
                else:
                    state = 3
                    state_change = True
            elif state == 3:
                if Enabled[3]:
                    if state_change:
                        print("Was Here")
                        GLib.idle_add(redraw_screen,Q1)
                        Q1_yesTxt.set_text("")
                        Q1_noTxt.set_text("")
                        Q1_begintxt.set_text("START")
                        Q1_txt.set_markup(SurveyPrompt)
                        state_change = False 
                else:
                    state = 4
                    state_change = True                          
            elif state == 4:
                if Enabled[4]:
                    if state_change:
                        print("Was Here")
                        GLib.idle_add(redraw_screen,Q1)
                        Q1_yesTxt.set_text("")
                        Q1_noTxt.set_text("")
                        Q1_begintxt.set_text("START")
                        Q1_txt.set_markup(SurveyPrompt)
                        state_change = False
                        q_num = 0
                        progress = 0
                        Answer = 0                    
                    time.sleep(0.1)
                    if q_num  == 0:                
                        GLib.idle_add(update_begin,start_survey_msg)
                    else:
                        GLib.idle_add(update_progess)

                    if Answer == 1:
                        time.sleep(0.5)
                        if (q_num == (len(Questions))):
                            state = 0
                            print ("changing state")
                            state_change = True 
                        else:
                            Q1_txt.set_markup(Questions[q_num])
                            Q1_yesTxt.set_text("YES")
                            Q1_noTxt.set_text("NO")
                            Q1_begintxt.set_text("")
                            q_num = q_num + 1
                            progress = 0
                            Answer = 0
                            time.sleep(0.5)                       
                    elif Answer == 2:
                        state = 0
                        state_change = True
                else :
                    state = 0
                    state_change = True
    def MyRFID() :
        # SPI connection:
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        print(spi)
        irq_pin = DigitalInOut(board.D17)
        cs_pin = DigitalInOut(board.D5)
        print(cs_pin)
        pn532 = PN532_SPI(spi, cs_pin, debug=False, irq=irq_pin)
        ic, ver, rev, support = pn532.firmware_version
        print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))
        # Configure PN532 to communicate with MiFare cards
        pn532.SAM_configuration()
        pn532.listen_for_passive_target()
        print("Waiting for RFID/NFC card...")
        run_once = True
        while True:
            # Check if a card is available to read
            if irq_pin.value == 0:
                uid = pn532.get_passive_target()
                print("Found card with UID:", [hex(i) for i in uid])
                # Start listening for a card again
                pn532.listen_for_passive_target()
 
            time.sleep(0.1)

    win.show_all()
    
    thread = threading.Thread( target = MyThread )
    rfid_thread = threading.Thread(target=MyRFID)
    thread.daemon=True
    rfid_thread.daemon=True 
    thread.start()
    rfid_thread.start()



def main():
    
    bus.write_byte(STM32_ADDRESS, 0x03)
    app_main()
    Gtk.main()
    cam.release()
    


if __name__ == '__main__':
    main()
