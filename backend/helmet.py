"""Annotation-assisted research model; cannot localize heads or issue violations."""
import cv2,numpy as np,hashlib,json
from pathlib import Path
def feature(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
    gray=cv2.resize(gray,(64,64)).astype(np.float32)
    gy,gx=np.gradient(gray);mag=np.hypot(gx,gy);bins=((np.arctan2(gy,gx)%np.pi)*9/np.pi).astype(int)%9
    cells=np.zeros((8,8,9),np.float32)
    for y in range(8):
        for x in range(8):cells[y,x]=np.bincount(bins[y*8:y*8+8,x*8:x*8+8].ravel(),weights=mag[y*8:y*8+8,x*8:x*8+8].ravel(),minlength=9)
    blocks=[]
    for y in range(7):
        for x in range(7):
            block=cells[y:y+2,x:x+2].ravel();blocks.append(block/np.sqrt(np.dot(block,block)+1e-5))
    return np.concatenate(blocks)

class HeadClassifier:
    def __init__(self):
        root=Path(__file__).resolve().parents[1]
        self.report=json.loads((root/"artifacts/helmet-classifier-report.json").read_text())
        path=root/"models/helmet-head-classifier.npz"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=self.report["sha256"]:raise ValueError("Classifier checksum mismatch")
        with np.load(path,allow_pickle=False) as model:
            self.weights=model["weights"].copy();self.mean=model["mean"].copy();self.scale=model["scale"].copy();self.bias=float(model["bias"])
    def predict(self,image):
        score=float(((feature(image)-self.mean)/self.scale)@self.weights+self.bias)
        positive=float(1/(1+np.exp(-np.clip(score,-30,30))))
        return {"prediction":"Without Helmet" if positive>=.5 else "With Helmet","unhelmeted_score":round(positive,4)}
