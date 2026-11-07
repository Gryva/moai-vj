# PHONE DRAWING - Script TOP callbacks (phonedraw_cb, synced to this file)
import numpy as np
BLACK = np.zeros((360, 640, 4), np.uint8)
def onSetupParameters(scriptOp): return
def onPulse(par): return
def onCook(scriptOp):
    F = op('/project1/remote_cb').module.DRAWF
    img = F.get('img')
    scriptOp.copyNumpyArray(img if img is not None else BLACK)
    F['new'] = False
