uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
uniform vec4 uQ;   // x drawing amount
uniform vec4 uO; uniform vec4 uO2; uniform vec4 uO3;   // layer order, back to front: 1 3D models, 2 phone camera, 5 drawing, 11-16 media layers 1-6, 0 = empty
uniform vec4 uA;    // amounts: x 3D models, y camera
uniform vec4 uS;    // effect chain (1-4, 0 none) of x 3D models, y camera, z drawing;  w = isolate this layer id (the per-layer chains)
uniform vec4 uOp;   // brightness: x 3D models, y camera, z drawing  (1 = as is, <1 see-through, >1 brighter)
uniform vec4 uF2; uniform vec4 uF5;                     // 2D framing of camera / drawing: zoom, x, y, rotate deg
uniform vec4 uMA1; uniform vec4 uMA2;                   // media layers 1-6: amount (0 = off or in 3D)
uniform vec4 uMS1; uniform vec4 uMS2;                   // media layers 1-6: effect chain
uniform vec4 uMO1; uniform vec4 uMO2;                   // media layers 1-6: brightness
uniform vec4 uMM1; uniform vec4 uMM2;                   // media layers 1-6: 1 = 3D object (input is its own render, premultiplied)
uniform vec4 uMF1; uniform vec4 uMF2; uniform vec4 uMF3; uniform vec4 uMF4; uniform vec4 uMF5; uniform vec4 uMF6;   // media framing
uniform vec4 uAL1; uniform vec4 uAL2;                   // opacity: media 1-4 | media 5, 6, 3D models, drawing
uniform vec4 uBL1; uniform vec4 uBL2;                   // blend mode, same order: 0 normal 1 add 2 screen 3 multiply 4 overlay 5 difference 6 lighten 7 darken
uniform vec4 uTX; uniform vec4 uTS;                     // text layers 1-3 drawn inside the stack (behind something, or in 3D): on, effect chain
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


// LAYERED SOURCE  inputs: 0 3D render (premultiplied), 1 phone camera / clip, 2 drawing, 3-8 media layers 1-6 (keyed, straight alpha),
// 9-12 the four per-layer effect chains (premultiplied RGBA), 13-15 text layers 1-3 (premultiplied; ids 21-23)
// uP.x camera blend: 1/2 normal, 3 blend (screen), 4 mask   uP.y mirror (+1, camera only) + whole image (+2)
vec2 frame(vec2 uv, vec4 f){
  vec2 res = uTD2DInfos[0].res.zw; float asp = res.x / res.y;
  vec2 q = uv - 0.5 - vec2(f.y, f.z) * 0.5; q.x *= asp;
  float r = radians(-f.w); q = mat2(cos(r), sin(r), -sin(r), cos(r)) * q; q.x /= asp;
  return q / max(0.05, abs(f.x)) + 0.5;                  // zoom < 0 = the same zoom, 'whole picture' framing
}
vec4 tin(int i, vec2 p){
  p = clamp(p, 0.0, 1.0);
  if (i == 1) return texture(sTD2DInputs[1], p);
  if (i == 3) return texture(sTD2DInputs[3], p); if (i == 4) return texture(sTD2DInputs[4], p);
  if (i == 5) return texture(sTD2DInputs[5], p); if (i == 6) return texture(sTD2DInputs[6], p);
  if (i == 7) return texture(sTD2DInputs[7], p); return texture(sTD2DInputs[8], p);
}
vec4 fitTex(int i, vec2 uv, bool mir, bool whole){       // .rgb colour, .a = alpha (keyed alpha x inside the picture)
  vec2 r0 = uTD2DInfos[0].res.zw, r1 = uTD2DInfos[i].res.zw;
  float a0 = r0.x / r0.y, a1 = r1.x / r1.y;
  bool fit = uP.y > 1.5 || whole;                        // whole: the full picture fits (bars), else it fills the screen (crops)
  vec2 q = uv - 0.5;
  if (fit) { if (a1 > a0) q.y *= a1 / a0; else q.x *= a0 / a1; }
  else     { if (a1 > a0) q.x *= a0 / a1; else q.y *= a1 / a0; }
  if (mir) q.x = -q.x;
  vec2 p = q + 0.5;
  float inside = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0)
               * step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
  vec4 t = tin(i, p);
  return vec4(t.rgb, (i == 1 ? 1.0 : t.a) * inside);
}
float pick4(vec4 a, vec4 b, int j){ return j == 0 ? a.x : j == 1 ? a.y : j == 2 ? a.z : j == 3 ? a.w : j == 4 ? b.x : b.y; }
vec4 mframe(int j){ return j == 0 ? uMF1 : j == 1 ? uMF2 : j == 2 ? uMF3 : j == 3 ? uMF4 : j == 4 ? uMF5 : uMF6; }
vec4 layerPM(int id, vec2 uv){                 // one layer on its own, premultiplied
  if (id == 1) return texture(sTD2DInputs[0], uv) * clamp(uA.x, 0.0, 1.0);
  if (id == 2) { vec4 c = fitTex(1, frame(uv, uF2), mod(uP.y, 2.0) > 0.5, false); float a = c.a * clamp(uA.y, 0.0, 1.0); return vec4(c.rgb * a, a); }
  if (id == 5) { vec2 p = frame(uv, uF5); float ins = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0);
                 vec3 d = clamp(texture(sTD2DInputs[2], clamp(p, 0.0, 1.0)).rgb * uQ.x, 0.0, 1.0) * ins; return vec4(d, max(d.r, max(d.g, d.b))); }
  if (id >= 11 && id <= 16) { int j = id - 11; float k = clamp(pick4(uMA1, uMA2, j), 0.0, 1.0); if (k < 0.002) return vec4(0.0);
                 if (pick4(uMM1, uMM2, j) > 0.5) return tin(3 + j, uv) * k;
                 vec4 c = fitTex(3 + j, frame(uv, mframe(j)), false, mframe(j).x < 0.0); float a = c.a * k; return vec4(c.rgb * a, a); }
  if (id >= 21 && id <= 23) { int j = id - 21; float k = j == 0 ? uTX.x : j == 1 ? uTX.y : uTX.z; if (k < 0.5) return vec4(0.0);
                 return j == 0 ? texture(sTD2DInputs[13], uv) : j == 1 ? texture(sTD2DInputs[14], uv) : texture(sTD2DInputs[15], uv); }
  return vec4(0.0);
}
int slotOf(int id){ return int(floor((id == 1 ? uS.x : id == 2 ? uS.y : id == 5 ? uS.z : (id >= 11 && id <= 16) ? pick4(uMS1, uMS2, id - 11) : id == 21 ? uTS.x : id == 22 ? uTS.y : id == 23 ? uTS.z : 0.0) + 0.5)); }
float opOf(int id){ return id == 1 ? uOp.x : id == 2 ? uOp.y : id == 5 ? uOp.z : (id >= 11 && id <= 16) ? pick4(uMO1, uMO2, id - 11) : 1.0; }
vec4 slotTex(int s, vec2 uv){
  return s == 1 ? texture(sTD2DInputs[9], uv) : s == 2 ? texture(sTD2DInputs[10], uv) : s == 3 ? texture(sTD2DInputs[11], uv) : texture(sTD2DInputs[12], uv);
}
vec3 layer(int id, vec2 uv, vec3 o){
  if (id < 1) return o;
  int s = slotOf(id);
  vec4 L = s > 0 ? slotTex(s, uv) : layerPM(id, uv);
  if (L.a < 0.0005 && max(L.r, max(L.g, L.b)) < 0.0005) return o;
  float op = opOf(id); L.rgb *= max(op, 0.0);                                          // brightness: darker / brighter, not see-through
  int bi = id == 1 ? 6 : id == 5 ? 7 : (id >= 11 && id <= 16) ? id - 11 : -1;
  if (bi >= 0) {                                                                         // each layer: opacity + blend mode
    float al = bi < 4 ? uAL1[bi] : uAL2[bi - 4]; L *= clamp(al, 0.0, 1.0);
    int bm = int((bi < 4 ? uBL1[bi] : uBL2[bi - 4]) + 0.5);
    vec3 c = clamp(L.rgb / max(L.a, 0.0001), 0.0, 4.0); float a = clamp(L.a, 0.0, 1.0);
    if (id == 5) a = max(a, max(L.r, max(L.g, L.b)));
    if (bm == 1) return o + L.rgb;
    if (bm == 2) return 1.0 - (1.0 - o) * (1.0 - clamp(L.rgb, 0.0, 1.0));
    if (bm == 3) return mix(o, o * c, a);
    if (bm == 4) return mix(o, mix(2.0 * o * c, 1.0 - 2.0 * (1.0 - o) * (1.0 - c), step(0.5, o)), a);
    if (bm == 5) return mix(o, abs(o - c), a);
    if (bm == 6) return mix(o, max(o, c), a);
    if (bm == 7) return mix(o, min(o, c), a);
  }
  if (id == 2) {
    int m = int(floor(uP.x + 0.5));
    if (m == 3) return 1.0 - (1.0 - o) * (1.0 - clamp(L.rgb, 0.0, 1.0) * 0.85);
    if (m == 4) { vec3 c = L.rgb / max(L.a, 0.001); return mix(o, o * smoothstep(0.08, 0.65, luma(c)) * 1.6 + c * 0.08, clamp(L.a, 0.0, 1.0)); }
  }
  return o * (1.0 - clamp(L.a, 0.0, 1.0)) + L.rgb;                                     // premultiplied over
}
void main(){
  vec2 uv = vUV.st;
  int iso = int(floor(uS.w + 0.5));
  if (iso > 0) { fragColor = TDOutputSwizzle(layerPM(iso, uv)); return; }
  vec3 o = vec3(0.0);
  float ids[12] = float[12](uO.x, uO.y, uO.z, uO.w, uO2.x, uO2.y, uO2.z, uO2.w, uO3.x, uO3.y, uO3.z, uO3.w);
  for (int i = 0; i < 12; i++) o = layer(int(ids[i] + 0.5), uv, o);
  fragColor = TDOutputSwizzle(vec4(o, 1.0));
}
