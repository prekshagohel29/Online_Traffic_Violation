"""CPU OpenCV DNN inference. YOLOX COCO weights, no simulated predictions."""
import os, time, hashlib, subprocess, shutil, re, io
from pathlib import Path
import cv2
import numpy as np
from .rules import Tracker, evaluate

MODEL_SHA='c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063'
MODEL_VERSION='opencv-zoo-yolox-2022nov:'+MODEL_SHA[:12]
COCO={0:'person',1:'bicycle',2:'car',3:'motorcycle',5:'bus',7:'truck'}
class Detector:
    def __init__(self,path):
        self.path=Path(path); self.error=None; self.net=None
        cv2.setNumThreads(int(os.getenv('CV_THREADS','2')))
        try:
            if hashlib.sha256(self.path.read_bytes()).hexdigest()!=MODEL_SHA: raise ValueError('Object detector checksum mismatch')
            self.net=cv2.dnn.readNetFromONNX(str(self.path))
        except Exception:
            self.error='Object detector missing or invalid. Run python -m scripts.fetch_assets.'
        grids=[]; steps=[]
        for stride in (8,16,32):
            yy,xx=np.indices((640//stride,640//stride))
            grids.append(np.stack([xx.ravel(),yy.ravel()],axis=1)); steps.extend([stride]*xx.size)
        self.grid=np.concatenate(grids); self.steps=np.asarray(steps,dtype=np.float32).reshape(-1,1)
    @property
    def ready(self): return self.net is not None
    def detect(self,image,threshold=.45):
        if not self.ready: raise RuntimeError(self.error)
        height,width=image.shape[:2]; scale=min(640/width,640/height)
        # YOLOX Zoo uses RGB float input in [0,255], top-left letterbox padding.
        canvas=np.full((640,640,3),114,np.uint8)
        rh,rw=int(height*scale),int(width*scale)
        canvas[:rh,:rw]=cv2.resize(image,(rw,rh))
        blob=cv2.dnn.blobFromImage(canvas,1.0,(640,640),swapRB=True,crop=False)
        self.net.setInput(blob); predictions=self.net.forward()[0]
        centers=(predictions[:,:2]+self.grid)*self.steps
        sizes=np.exp(np.clip(predictions[:,2:4],-20,20))*self.steps
        boxes=np.concatenate([centers-sizes/2,sizes],axis=1)
        probs=predictions[:,5:]*predictions[:,4,None]
        ids=probs.argmax(axis=1); scores=probs.max(axis=1)
        outputs=[]
        for cls,label in COCO.items():
            mask=np.where((ids==cls)&(scores>=threshold))[0]
            if not len(mask): continue
            keep=cv2.dnn.NMSBoxes(boxes[mask].tolist(),scores[mask].tolist(),threshold,.5)
            for index in np.asarray(keep).reshape(-1):
                i=mask[index]; x,y,w,h=boxes[i]/scale
                x1=max(0,min(width,float(x))); y1=max(0,min(height,float(y)))
                x2=max(x1,min(width,float(x+w))); y2=max(y1,min(height,float(y+h)))
                if x2-x1<2 or y2-y1<2: continue
                outputs.append({'class':label,'confidence':float(scores[i]),'box':[x1/width,y1/height,(x2-x1)/width,(y2-y1)/height]})
        return outputs

def ocr_plate(image,box):
    """Optional real Tesseract OCR of contour proposals. Experimental, never an owner lookup.

    This is a visible integration fallback, not a trained plate detector. Proposals
    and raw OCR remain reviewable. Empty output means unreadable, not no plate.
    """
    executable=os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
    if not executable: return [],[]
    height,width=image.shape[:2]; x,y,w,h=box
    crop=image[int(y*height):int((y+h)*height),int(x*width):int((x+w)*width)]
    if crop.size==0: return [],[]
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    if cv2.Laplacian(gray,cv2.CV_64F).var()<50: return [],[]
    edges=cv2.Canny(gray,60,160); contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    proposals=[]
    for contour in sorted(contours,key=cv2.contourArea,reverse=True)[:40]:
        px,py,pw,ph=cv2.boundingRect(contour)
        if 2<=pw/max(ph,1)<=6 and pw>=45 and ph>=12 and .002< pw*ph/(crop.shape[0]*crop.shape[1])<.25:
            proposals.append(crop[py:py+ph,px:px+pw])
    raw=[]; saved=[]
    for proposal in proposals[:3]:
        _,encoded=cv2.imencode('.png',cv2.resize(proposal,None,fx=2,fy=2))
        try:
            result=subprocess.run([executable,'stdin','stdout','--psm','7','-c','tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'],input=encoded.tobytes(),capture_output=True,timeout=3,check=True)
            reading=result.stdout.decode('utf-8',errors='replace').strip(); normalized=re.sub('[^A-Z0-9]','',reading.upper())
            raw.append({'raw':reading,'normalized':normalized,'status':'uncertain','method':'contour-proposal+tesseract','indian_format_hint':bool(re.fullmatch(r'(?:[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}|[0-9]{2}BH[0-9]{4}[A-Z]{1,2})',normalized))})
            saved.append(proposal)
        except (subprocess.SubprocessError,OSError): pass
    return raw,saved

def annotate(image,tracks,config,source_time,seq):
    frame=image.copy(); h,w=frame.shape[:2]
    for key in ('lane','restricted_zone','parking_zone','stop_line','line_a','line_b','direction'):
        if config.get(key):
            pts=np.asarray([[int(p[0]*w),int(p[1]*h)] for p in config[key]],np.int32)
            cv2.polylines(frame,[pts],key in ('lane','restricted_zone','parking_zone'),(0,210,255),2)
    for tr in tracks:
        x,y,bw,bh=tr['box']; a=(int(x*w),int(y*h)); b=(int((x+bw)*w),int((y+bh)*h))
        cv2.rectangle(frame,a,b,(70,220,100),2)
        cv2.putText(frame,f"{tr['class']} #{tr['id']} {tr['confidence']:.2f}",(a[0],max(15,a[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,(70,220,100),1)
    cv2.putText(frame,f'Source {source_time:.3f}s | frame {seq} | EXPERIMENTAL',(10,h-15),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    return frame

def process_frame(detector,image,t,state,config,signal=None):
    start=time.perf_counter(); detections=detector.detect(image,config.get('confidence',.45))
    tracker=Tracker(state); tracks=tracker.update(detections,t,config.get('max_gap',1.5)); events=[]
    for tr in tracks:
        for event in evaluate(tr,config,signal):
            event['confidence']=tr['confidence']; event['box']=tr['box']; event['class']=tr['class']; event['trajectory']=tr['history'][-30:]
            events.append(event)
    return tracks,events,tracker.state,(time.perf_counter()-start)*1000
