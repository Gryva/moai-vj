# PHONE RELAY - MQTT Client DAT callbacks (remote_mqtt_cb, synced to this file)
# TouchDesigner <-> public broker <-> phone page on GitHub Pages. Topic = moaivj/<secret key>
import json

def _R(): return op('/project1/remote_cb').module

def onConnect(dat):
    R = _R()
    dat.subscribe(R.relayBase() + '/cmd', qos=0)
    dat.subscribe(R.relayBase() + '/cam', qos=0)
    dat.subscribe(R.relayBase() + '/draw', qos=0)
    dat.publish(R.relayBase() + '/state', b'', qos=0, retain=True)     # wipe any old public copy
    print('PHONE RELAY connected ->', R.relayLink())

def onConnectFailure(dat, msg): print('PHONE RELAY connect failed:', msg)
def onConnectionLost(dat, msg): print('PHONE RELAY lost:', msg)
def onSubscribe(dat): return
def onSubscribeFailure(dat, msg): print('PHONE RELAY subscribe failed:', msg)
def onUnsubscribe(dat): return
def onUnsubscribeFailure(dat, msg): return
def onPublish(dat): return

def onMessage(dat, topic, payload, qos, retained, dup):
    if retained: return
    if topic.endswith('/cam'):
        _R().camFrame(payload); return
    if topic.endswith('/draw'):
        _R().drawFrame(payload); return
    try:
        msg = json.loads(payload.decode('utf-8') if isinstance(payload, (bytes, bytearray)) else payload)
    except Exception:
        return
    R = _R()
    R.SEEN[dat.name] = __import__('time').perf_counter()     # remember which relay this phone uses
    R.handle(msg, lambda o: R._publish(o))
