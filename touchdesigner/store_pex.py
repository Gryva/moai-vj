# CONTROLS -> Safety page buttons  (store_pex Parameter Execute DAT, synced to td/store_pex.py)
def onPulse(par):
    E = op('/project1/fx_engine').module
    n = par.name
    if n == 'Storeundo': E.storeUndo()
    elif n == 'Storereload': E.storeReload()
    elif n == 'Storebackup': E.storeBackupNow()
    elif n == 'Storeopen':
        import os
        try: os.startfile(E.HIST_DIR)
        except Exception as e: print('open folder failed', e)
    elif n == 'Storerestore':
        h = E.storeHistory(400)
        i = int(par.owner.par.Storepick.eval())
        if 0 <= i < len(h): E.storeRestore(h[i]['f'])
    elif n == 'Storelist':
        for i, h in enumerate(E.storeHistory(40)): print(i, h['when'], h['why'])
    return

def onValueChange(par, prev): return
def onExpressionChange(par, val, prev): return
def onExportChange(par, val, prev): return
def onEnableChange(par, val, prev): return
def onModeChange(par, val, prev): return
