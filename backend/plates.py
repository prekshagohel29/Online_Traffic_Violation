"""Trained plate localization plus real neural OCR; suggestions never establish ownership."""
import os,json,hashlib,re
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
class PlateReader:
    def __init__(self):
        self.ready=False;self.error='Plate models not provisioned';self.detector=None;self.ocr=None
        path=ROOT/'models/plates'
        try:
            manifest=json.loads((path/'manifest.json').read_text())
            for item in manifest:
                target=ROOT/item['file']
                if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Checksum mismatch')
            import openvino as ov
            core=ov.Core();model=core.read_model(path/'vehicle-license-plate-detection-barrier-0106.xml')
            self.detector=core.compile_model(model,'CPU',{'INFERENCE_NUM_THREADS':2,'PERFORMANCE_HINT':'LATENCY'})
            from fast_plate_ocr import LicensePlateRecognizer
            import onnxruntime as ort
            opts=ort.SessionOptions();opts.intra_op_num_threads=2
            self.ocr=LicensePlateRecognizer(onnx_model_path=path/'cct_xs_v2_global.onnx',plate_config_path=path/'cct_xs_v2_global_plate_config.yaml',device='cpu',sess_options=opts)
            self.ready=True;self.error=None
        except Exception as exc:self.error='Plate runtime unavailable: '+type(exc).__name__
    def read(self,image,box=None):
        if not self.ready:return [],[]
        h,w=image.shape[:2];offset=[0,0]
        if box:
            x,y,bw,bh=box;x1=max(0,int(x*w));y1=max(0,int(y*h));x2=min(w,int((x+bw)*w));y2=min(h,int((y+bh)*h));image=image[y1:y2,x1:x2];offset=[x1,y1]
        if image.size==0:return [],[]
        height,width=image.shape[:2]
        output=self.detector([cv2.resize(image,(300,300)).astype(np.float32)[None]])
        detections=next(iter(output.values())).reshape(-1,7);readings=[];crops=[]
        for _,label,confidence,x1,y1,x2,y2 in detections:
            if int(label)!=2 or confidence<.45:continue
            a=max(0,int(x1*width));b=max(0,int(y1*height));c=min(width,int(x2*width));d=min(height,int(y2*height));crop=image[b:d,a:c]
            if crop.size==0 or crop.shape[1]<24 or crop.shape[0]<8:continue
            try:
                reading=self.ocr.run_one(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB),return_confidence=True)
                normalized=re.sub('[^A-Z0-9]','',reading.plate.upper());probs=reading.char_probs
                mean=float(np.mean(probs)) if probs is not None else None
                readings.append({'raw':reading.plate,'normalized':normalized,'status':'unreviewed_suggestion',
                    'detection_confidence':float(confidence),'ocr_character_mean':mean,'method':'Intel MobileNetSSD plate detector + CCT-XS neural OCR',
                    'box_pixels':[a+offset[0],b+offset[1],c+offset[0],d+offset[1]],
                    'limitation':'Detector was trained for frontal Chinese barrier-camera views; Indian-camera performance is unvalidated'})
                crops.append(crop)
            except Exception:continue
        return readings[:4],crops[:4]
