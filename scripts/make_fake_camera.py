"""Prepare a repeatable CC0 video camera fixture for browser tests only."""
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[1]
def main():
    dest=ROOT/'data/browser-qa/fake-camera.y4m';dest.parent.mkdir(parents=True,exist_ok=True)
    capture=cv2.VideoCapture(str(ROOT/'samples/rush-hour.webm'))
    try:
        with dest.open('wb') as output:
            output.write(b'YUV4MPEG2 W640 H360 F5:1 Ip A1:1 C420jpeg\n')
            for _ in range(20):
                ok,image=capture.read()
                if not ok:raise RuntimeError('Included CC0 clip is needed for the browser camera fixture')
                image=cv2.resize(image,(640,360));output.write(b'FRAME\n');output.write(cv2.cvtColor(image,cv2.COLOR_BGR2YUV_I420).tobytes())
    finally:capture.release()
if __name__=='__main__':main()
