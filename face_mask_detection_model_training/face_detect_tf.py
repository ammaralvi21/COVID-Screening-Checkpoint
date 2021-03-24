# MIT License
#
# Copyright (c) 2019 Iván de Paz Centeno
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



import cv2
import os
import tensorflow as tf
import numpy as np
from tensorflow import keras
from mtcnn import MTCNN

model = keras.models.load_model('face_mask_detection_model')

detector = MTCNN(min_face_size = 100)
cap = cv2.VideoCapture(0)

#scale_percent = 60 # percent of original size

#def change_res(width, height):
  #  cap.set(3, width)
 #   cap.set(4, height)


#change_res(224, 224)

# font 
font = cv2.FONT_HERSHEY_SIMPLEX 
  
# org 
org = (00, 00) 
  
# fontScale 
fontScale = 0.6
   
# Red color in BGR 
color = (0, 0, 255) 
  
# Line thickness of 2 px 
thickness = 1
minimum_brightness = 1.1

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here 
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # loop over various values of gamma

    #image = cv2.resize(image, (0,0), fx = 0.3, fy = 0.3)
    result = detector.detect_faces(image)
    

   # model.predict(crop_img)
    if result:
    # Result is an array with all the bounding boxes detected. We know that for 'ivan.jpg' there is only one.
        bounding_box = result[0]['box']
        #keypoints = result[0]['keypoints']
        x1 = bounding_box[0] - 20
        y1 = bounding_box[1] - 10
        x2 = bounding_box[0] + bounding_box[2] + 20
        y2 = bounding_box[1] + bounding_box[3] + 50
        
        crop_img = image[y1:y2, x1:x2]

        cols, rows, x = crop_img.shape
        if (cols > 0) and (rows > 0):
            brightness = np.sum(crop_img) / (255 * cols * rows)

        ratio = brightness / minimum_brightness

        if ratio < 1:
            image = cv2.convertScaleAbs(image, alpha = (1 / ratio), beta = 0)
            crop_img = image[y1:y2, x1:x2]

        cv2.putText(image, "={}".format(ratio), (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        #
        # Display the resulting frame
        if crop_img.size > 0:
            dim = (224, 224)
            img_resized = cv2.resize(crop_img, dim, interpolation=cv2.INTER_LINEAR)
            img_resized = np.expand_dims(img_resized, axis=0)
           
            prob = model.predict(img_resized)
            predIdxs = np.argmax(prob, axis=1)
            org = (x1 - 10, y1 - 45)

            if predIdxs == 1:
                color = (0, 255, 0)
                image = cv2.rectangle(image, (x1,y1), (x2,y2), color, 2)
                #cv2.rectangle(image, (x, x), (x + w, y + h), (0,0,0), -1)
                cv2.rectangle(image, (org[0], org[1] - 20), (x2 + 80, y1), (0,0,0), -1)
                image = cv2.putText(image, "Mask Detected", org, font, fontScale, color, thickness, cv2.LINE_AA, False)
                image = cv2.putText(image, "Stay still for recognition", (org[0], org[1] + 20), font, fontScale, color, thickness, cv2.LINE_AA, False)
                image = cv2.putText(image, str(prob[0][1]), (org[0],org[1] + 40), font, fontScale, color, thickness, cv2.LINE_AA, False)  
            else:
                color = (255, 0, 0)
                image = cv2.rectangle(image, (x1,y1), (x2,y2), color, 2)
                cv2.rectangle(image, (org[0], org[1] - 20), (x2 + 80, y1), (0,0,0), -1)
                image = cv2.putText(image, "Mask is incorrectly/not worn", org, font, fontScale, color, thickness, cv2.LINE_AA, False)
                image = cv2.putText(image, "Please hold your face steady", (org[0], org[1] + 20), font, fontScale, color, thickness, cv2.LINE_AA, False)
                image = cv2.putText(image, str(prob[0][0]), (org[0], org[1] + 40), font, fontScale, color, thickness, cv2.LINE_AA, False)  

            #print(predIdxs)
            cv2.imshow('frame',cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        else:
            cv2.imshow('frame',cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        #predIdxs = model.predict(crop_img)
       # print(predIdxs)
        #predIdxs = np.argmax(predIdxs, axis=1)
        #print(predIdxs)
    else:
         cv2.imshow('frame',cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
