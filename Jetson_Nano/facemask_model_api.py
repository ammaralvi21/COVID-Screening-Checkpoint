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
import onnxruntime as rt

minimum_brightness = 1.6

class  FaceMask:
    def __init__(self,path):
        # load the recognition network
        print("loading inference recognition network")
        self.sess = rt.InferenceSession("model/onnx_face_mask_model_ops9_2.onnx")

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
        self.x1, self.y1, self.x2, self.y2 =    (int(roi[0]) - 5), \
                                                (int(roi[1]) - 5), \
                                                (int(roi[2]) +int(roi[0])+ 20), \
                                                (int(roi[3]) + int(roi[1]) + 10) 
   
        self.crop_img = self.image[self.y1:self.y2, self.x1:self.x2]
	    
    def display_info(self):

        cv2.rectangle(self.image,
                     (self.x1, self.y1 - 60),
                     (self.x1 + 120, self.y1),
                     (0,0,0),
                     -1)

        cv2.putText(self.image, 
                    str(round(self.confidence*100,2)) + "%", 
                    (self.x1, self.y1 - 20),
                    self.font, 
                    self.fontScale, 
                    (self.color), 
                    self.thickness, 
                    cv2.LINE_AA, 
                    False)

        cv2.rectangle(self.image, 
                    (30, 630), 
                    (1250, 670),
                    (0,0,0), -1)

        cv2.putText(self.image,
                    str(self.class_desc), 
                    (40, 660), 
                    self.font, 
                    self.fontScale, 
                    self.color, 
                    self.thickness, 
                    cv2.LINE_AA,
                    False)
	
        cv2.rectangle(self.image,
                    (self.x1, self.y1), 
                    (self.x2, self.y2),
                    self.color,
                    2)
    
    def detect(self,roi,image):
        self.image = image
        self.preprocess(roi)
        if self.crop_img.size > 0:
            self.out_of_range = 0
            cols, rows, x = self.crop_img.shape
            #brightness = np.sum(self.crop_img) / (255 * cols * rows)
            #ratio = brightness / 1.5
            #if ratio < 1:
            #    self.image = cv2.convertScaleAbs(self.image, alpha = (1 / ratio), beta = 0)
     
            dim = (224, 224)
            img_resized = cv2.resize(self.crop_img, dim, interpolation=cv2.INTER_LINEAR)
            img_resized = np.expand_dims(img_resized, axis=0)
            img_resized = np.asarray(img_resized, dtype="float32")
            pred_onx = self.sess.run(None, {'input_1:0': img_resized})
            self.class_id = np.argmax(pred_onx[0][0])


            
            if (self.class_id) :
                self.confidence = pred_onx[0][0][1]
                if self.confidence > 0.8:
                    self.class_desc = "Face Mask is being detected, hold your face steady during detection"
                    self.color = (0, 255, 0)
                else:
                    self.color = (26, 209, 255)
                    self.class_desc = "   Confidence is below 80%, please wear your face mask correctly   "
            else:
                self.color = (0, 0, 255)
                self.class_desc =     "  Face Mask is not detected, please wear your face mask correctly  "
                self.confidence = pred_onx[0][0][0]

            self.display_info()
        else:
            self.out_of_range = 1
            print("out of range ")

        return self.image, self.confidence, self.class_id

        

