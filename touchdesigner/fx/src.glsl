uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
uniform vec4 uQ;   // x drawing amount
uniform vec4 uO;   // layer order, back to front: ids 1 3D models, 2 phone camera, 3 images, 4 videos, 5 drawing (0 = empty)
uniform vec4 uO2;  // order slots 5..8
uniform vec4 uA;   // amounts: x 3D models, y camera, z images, w videos
uniform vec4 uS;   // effect slot (1-4, 0 = none) of: x 3D models, y camera, z images, w videos
uniform vec4 uS2;  // x effect slot of the drawing, y = isolate this layer id (the per-layer effect chains)
uniform vec4 uF2; uniform vec4 uF3; uniform vec4 uF4; uniform vec4 uF5;   // 2D framing of camera / images / videos / drawing: zoom, x, y, rotate deg
layout(location = 0) out vec4 fragColor;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int i=0;i<5;i++){ v += a*vnoise(p); p *= 2.03; a *= 0.5; } return v; }
vec3 tex(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)).rgb; }
float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 hsv(float h, float s, float v){ vec3 k = clamp(abs(mod(h*6.0 + vec3(0,4,2), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1.0), k, s); }
vec2 PX(){ return uTD2DInfos[0].res.xy; }
vec2 RES(){ return uTD2DInfos[0].res.zw; }


// LAYERED SOURCE  inputs: 0 3D render (premultiplied), 1 phone camera / clip, 2 drawing, 3 images (keyed), 4 videos,
// 5-8 the four per-layer effect chains (premultiplied RGBA, same order as uS)
// uP.x camera blend: 1/2 normal, 3 blend (screen), 4 mask   uP.y mirror (+1, camera only) + whole image (+2)
vec2 frame(vec2 uv, vec4 f){
  vec2 res = uTD2DInfos[0].res.zw; float asp = res.x / res.y;
  vec2 q = uv - 0.5 - vec2(f.y, f.z) * 0.5; q.x *= asp;
  float r = radians(-f.w); q = mat2(cos(r), sin(r), -sin(r), cos(r)) * q; q.x /= asp;
  return q / max(0.05, f.x) + 0.5;
}
vec4 fitTex(int i, vec2 uv, bool mir){       // .rgb colour, .a = alpha (keyed alpha x inside the picture)
  vec2 r0 = uTD2DInfos[0].res.zw, r1 = uTD2DInfos[i].res.zw;
  float a0 = r0.x / r0.y, a1 = r1.x / r1.y;
  bool fit = uP.y > 1.5;
  vec2 q = uv - 0.5;
  if (fit) { if (a1 > a0) q.y *= a1 / a0; else q.x *= a0 / a1; }
  else     { if (a1 > a0) q.x *= a0 / a1; else q.y *= a1 / a0; }
  if (mir) q.x = -q.x;
  vec2 p = q + 0.5;
  float inside = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0)
               * step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
  vec4 t = i == 1 ? texture(sTD2DInputs[1], clamp(p, 0.0, 1.0)) : i == 3 ? texture(sTD2DInputs[3], clamp(p, 0.0, 1.0)) : texture(sTD2DInputs[4], clamp(p, 0.0, 1.0));
  return vec4(t.rgb, (i == 1 ? 1.0 : t.a) * inside);
}
vec4 layerPM(int id, vec2 uv){                 // one layer on its own, premultiplied
  if (id == 1) return texture(sTD2DInputs[0], uv) * clamp(uA.x, 0.0, 1.0);
  if (id == 2) { vec4 c = fitTex(1, frame(uv, uF2), mod(uP.y, 2.0) > 0.5); float a = c.a * clamp(uA.y, 0.0, 1.0); return vec4(c.rgb * a, a); }
  if (id == 3) { vec4 c = fitTex(3, frame(uv, uF3), false); float a = c.a * clamp(uA.z, 0.0, 1.0); return vec4(c.rgb * a, a); }
  if (id == 4) { vec4 c = fitTex(4, frame(uv, uF4), false); float a = c.a * clamp(uA.w, 0.0, 1.0); return vec4(c.rgb * a, a); }
  if (id == 5) { vec2 p = frame(uv, uF5); float ins = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0);
                 vec3 d = clamp(texture(sTD2DInputs[2], clamp(p, 0.0, 1.0)).rgb * uQ.x, 0.0, 1.0) * ins; return vec4(d, max(d.r, max(d.g, d.b))); }
  return vec4(0.0);
}
int slotOf(int id){ return int(floor((id == 1 ? uS.x : id == 2 ? uS.y : id == 3 ? uS.z : id == 4 ? uS.w : uS2.x) + 0.5)); }
vec4 slotTex(int s, vec2 uv){
  return s == 1 ? texture(sTD2DInputs[5], uv) : s == 2 ? texture(sTD2DInputs[6], uv) : s == 3 ? texture(sTD2DInputs[7], uv) : texture(sTD2DInputs[8], uv);
}
vec3 layer(int id, vec2 uv, vec3 o){
  if (id < 1 || id > 5) return o;
  int s = slotOf(id);
  vec4 L = s > 0 ? slotTex(s, uv) : layerPM(id, uv);
  if (L.a < 0.0005 && max(L.r, max(L.g, L.b)) < 0.0005) return o;
  if (id == 5) return 1.0 - (1.0 - o) * (1.0 - clamp(L.rgb, 0.0, 1.0));               // drawing: screen
  if (id == 2) {
    int m = int(floor(uP.x + 0.5));
    if (m == 3) return 1.0 - (1.0 - o) * (1.0 - clamp(L.rgb, 0.0, 1.0) * 0.85);
    if (m == 4) { vec3 c = L.rgb / max(L.a, 0.001); return mix(o, o * smoothstep(0.08, 0.65, luma(c)) * 1.6 + c * 0.08, clamp(L.a, 0.0, 1.0)); }
  }
  return o * (1.0 - clamp(L.a, 0.0, 1.0)) + L.rgb;                                     // premultiplied over
}
void main(){
  vec2 uv = vUV.st;
  int iso = int(floor(uS2.y + 0.5));
  if (iso > 0) { fragColor = TDOutputSwizzle(layerPM(iso, uv)); return; }
  vec3 o = vec3(0.0);
  float ids[8] = float[8](uO.x, uO.y, uO.z, uO.w, uO2.x, uO2.y, uO2.z, uO2.w);
  for (int i = 0; i < 8; i++) o = layer(int(ids[i] + 0.5), uv, o);
  fragColor = TDOutputSwizzle(vec4(o, 1.0));
}
