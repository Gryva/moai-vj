# PHONE CAMERA - Script TOP callbacks (phonecam_cb, synced to this file)
# Frames arrive as JPEG over the phone relay (remote_mqtt_cb -> remote_cb.camFrame), decoded there.
import numpy as np
BLACK = np.zeros((216, 384, 4), np.uint8)

def onSetupParameters(scriptOp): return
def onPulse(par): return

def onCook(scriptOp):
    F = op('/project1/remote_cb').module.CAMF
    img = F.get('img')
    scriptOp.copyNumpyArray(img if img is not None else BLACK)
    F['new'] = False
