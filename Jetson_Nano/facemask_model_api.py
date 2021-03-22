# MIT License
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
import numpy as np
import jetson.inference
import jetson.utils



#scale_percent = 60 # percent of original size

#def change_res(width, height):
  #  cap.set(3, width)
 #   cap.set(4, height)


#change_res(224, 224)

minimum_brightness = 1.6


myArg = ['facemask_model_api.py', '--model=model/resnet50.onnx', '--input_blob=input_0', '--output_blob=output_0', '--labels=labels.txt']
font = jetson.utils.cudaFont()

class  FaceMask:
    def __init__(self,path):
        # load the recognition network
        print("loading inference recognition network")
        self.net = jetson.inference.imageNet("googlenet", myArg)

        self.font = cv2.FONT_HERSHEY_DUPLEX    # font
        self.org = (00, 00)                     # org 
        self.fontScale = 1                    # fontScale 
        self.color = (0, 0, 255)                # Red color in BGR 
        self.thickness = 2
        self.dim = (224, 224)
        self.confidence = 0
        self.class_id = 0
        #self.cnt = 0


    def preprocess(self,roi):
        self.x1, self.y1, self.x2, self.y2 = (int(roi[0]) - 5), (int(roi[1]) - 5), (int(roi[2]) +int(roi[0])+ 20), (int(roi[3]) + int(roi[1]) + 10)    
        self.crop_img = self.image[self.y1:self.y2, self.x1:self.x2]
	    
    def display_info(self):
        cv2.rectangle(self.image, (self.x1, self.y1 - 60), (self.x1 + 120, self.y1), self.color, -1)
        cv2.putText(self.image, str(round(self.confidence*100,2)) + "%", (self.x1, self.y1 - 20), self.font, self.fontScale, (0,0,0), self.thickness, cv2.LINE_AA, False)
        cv2.rectangle(self.image, (30, 660), (1250, 700), self.color, -1)
        cv2.putText(self.image, str(self.class_desc), (40, 690), self.font, self.fontScale, (0,0,0), self.thickness, cv2.LINE_AA, False)
	
        cv2.rectangle(self.image, (self.x1, self.y1), (self.x2, self.y2), self.color, 2)
    
    def detect(self,roi,image):
        self.image = image
        self.preprocess(roi)
        if self.crop_img.size > 0:
            self.out_of_range = 0
            cols, rows, x = self.crop_img.shape
            brightness = np.sum(self.crop_img) / (255 * cols * rows)
            ratio = brightness / 1.5
            if ratio < 1:
                self.image = cv2.convertScaleAbs(self.image, alpha = (1 / ratio), beta = 0)     
            self.cudaImg = jetson.utils.cudaFromNumpy(cv2.cvtColor(self.crop_img, cv2.COLOR_BGR2RGB))
            self.class_id, self.confidence = self.net.Classify(self.cudaImg)
            self.class_desc = self.net.GetClassDesc(self.class_id)

            if(self.class_id) and (self.confidence > 0.8):
                self.color = (0, 255, 0)
                self.class_desc = "    Face Mask is being detected, keep your face steady    "
            elif(self.class_id) and (self.confidence <= 0.8):
                self.color = (26, 209, 255)
                self.class_desc = " Confidence is below 80%, please wear your mask correctly "
            else:
                self.color = (0, 0, 255)
                self.class_desc = "Face Mask is not detected, please wear face mask correctly"

            self.display_info()
        else:
            self.out_of_range = 1
            print("out of range ")

        return self.image, self.confidence, self.class_id

        

