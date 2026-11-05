"""Train and evaluate an annotation-assisted helmet/head classifier, not a live detector."""
import json,urllib.request,concurrent.futures,time,hashlib
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
BASE='https://huggingface.co/datasets/cute-face/bike-helmet-dataset/resolve/29338f31e9985da07bc6992dde0633676c7b6415/'
from backend.helmet import feature

def download(url,path):
    if path.exists():return
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Preksha-educational-classifier/2.0'}),timeout=35) as r:data=r.read(5*1024*1024)
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return
        except Exception:
            if attempt==3:raise
            time.sleep(2+attempt*2)
def load(split,limit):
    root=ROOT/'data/helmet-training'/split;root.mkdir(parents=True,exist_ok=True)
    download(BASE+split+'/_annotations.coco.json',root/'annotations.json')
    data=json.loads((root/'annotations.json').read_text());cats={x['id']:x['name'] for x in data['categories']}
    images=data['images'][:limit]
    def get(image):
        from urllib.parse import quote
        path=root/image['file_name'];download(BASE+split+'/'+quote(image['file_name']),path)
        frame=cv2.imread(str(path));features=[];labels=[]
        for a in data['annotations']:
            if a['image_id']!=image['id']:continue
            name=cats[a['category_id']]
            if name not in ('With Helmet','Without Helmet'):continue
            x,y,w,h=[int(v) for v in a['bbox']];crop=frame[max(0,y):y+h,max(0,x):x+w]
            if not crop.size or min(crop.shape[:2])<8:continue
            features.append(feature(crop));labels.append(0 if name=='With Helmet' else 1)
            if split=='train':features.append(feature(cv2.flip(crop,1)));labels.append(labels[-1])
        return features,labels,image['file_name'].split('.rf.')[0]
    x=[];y=[];sources=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for features,labels,source in pool.map(get,images):x.extend(features);y.extend(labels);sources.extend([source]*len(labels))
    print(split,len(images),'images',len(y),'head crops',flush=True)
    return np.asarray(x,np.float32),np.asarray(y,np.int32),sources
def main():
    cv2.setNumThreads(2)
    x,y,sources=load('train',240);vx,vy,vsources=load('valid',64);tx,ty,tsources=load('test',64)
    held=set(vsources+tsources);keep=np.asarray([s not in held for s in sources]);x=x[keep];y=y[keep]
    mean=x.mean(axis=0);scale=np.maximum(x.std(axis=0),.08);x=(x-mean)/scale;vx=(vx-mean)/scale;tx=(tx-mean)/scale
    # Balanced logistic classifier optimized with full-batch gradient descent.
    weights=np.zeros(x.shape[1],np.float32);bias=0.;best_loss=float('inf');best=None
    balance=np.where(y==1,len(y)/(2*max(1,(y==1).sum())),len(y)/(2*max(1,(y==0).sum())))
    for epoch in range(300):
        score=np.clip(x@weights+bias,-30,30);p=1/(1+np.exp(-score));grad=(p-y)*balance
        weights-=.035*(x.T@grad/len(y)+.002*weights);bias-=.035*grad.mean()
        vp=1/(1+np.exp(-np.clip(vx@weights+bias,-30,30)));loss=float(-np.mean(vy*np.log(vp+1e-8)+(1-vy)*np.log(1-vp+1e-8)))
        if loss<best_loss:best_loss=loss;best=(weights.copy(),bias,epoch)
    weights,bias,epoch=best;score=tx@weights+bias;pred=(score>0).astype(int)
    tp=int(((pred==1)&(ty==1)).sum());fp=int(((pred==1)&(ty==0)).sum());fn=int(((pred==0)&(ty==1)).sum());tn=int(((pred==0)&(ty==0)).sum())
    path=ROOT/'models/helmet-head-classifier.npz';np.savez_compressed(path,weights=weights,bias=bias,mean=mean,scale=scale)
    report={'model':'HOG64 + balanced logistic classifier','use':'Annotation-assisted head-crop classification; NOT automatic helmet violation detection',
        'dataset_url':'https://huggingface.co/datasets/cute-face/bike-helmet-dataset','revision':'29338f31e9985da07bc6992dde0633676c7b6415','license':'CC BY 4.0 mirror; original dataset declares Public Domain',
        'train_crops':len(y),'validation_crops':len(vy),'test_crops':len(ty),'train_source_images':len(set(np.asarray(sources)[keep])),
        'selected_epoch':epoch,'positive_class':'Without Helmet','tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':tp/max(1,tp+fp),'recall':tp/max(1,tp+fn),'accuracy':float((pred==ty).mean()),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'limitations':'Uses published head boxes. Event-level precision/recall and live head localization are not established. Filenames exclude exact train/held-out source overlap; source-video separation could not be established.'}
    (ROOT/'artifacts/helmet-classifier-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
