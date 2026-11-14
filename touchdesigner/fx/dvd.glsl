uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
layout(location = 0) out vec4 fragColor;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int i=0;i<5;i++){ v += a*vnoise(p); p *= 2.03; a *= 0.5; } return v; }
float gA = 0.0, gA1 = -1.0;   // alpha follows the samples, so a single layer keeps its see-through parts through the effect
vec3 tex(vec2 uv){ vec4 t = texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)); if (gA1 < 0.0) gA1 = t.a; gA = max(gA, t.a); return t.rgb; }
vec3 texK(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)).rgb; }
vec4 outc(vec2 uv0, vec3 c){ vec3 o = mix(texK(uv0), c, uMix);
  float a = min(gA, max(max(gA1, 0.0), max(o.r, max(o.g, o.b))));
  return vec4(o, clamp(mix(texture(sTD2DInputs[0], clamp(uv0, 0.0, 1.0)).a, a, uMix), 0.0, 1.0)); }
float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 hsv(float h, float s, float v){ vec3 k = clamp(abs(mod(h*6.0 + vec3(0,4,2), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1.0), k, s); }
vec2 PX(){ return uTD2DInfos[0].res.xy; }
vec2 RES(){ return uTD2DInfos[0].res.zw; }

vec3 rgb2hsv(vec3 c){ vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0); vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g)); vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r)); float d = q.x - min(q.w, q.y); float e = 1.0e-10; return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x); }
float ASP(){ vec2 r = RES(); return r.x / r.y; }
#define OUT(c) fragColor = TDOutputSwizzle(outc(vUV.st, (c)))

vec4 texA(vec2 uv){ return (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) ? vec4(0.0) : texture(sTD2DInputs[0], uv); }   // outside the picture = see-through
float d2(float v, float d){ return floor(v / d + 0.001); }
// DVD BOUNCE  the picture flies around and bounces off the screen edges, like the old DVD screensaver.
// uP.x = speed * 100 + size (0-99), uP.y = angle * 100 + colour change on each bounce (0 off / 1 on), uP.z = copies (+1 every corner hit)
uniform vec4 uBB;   // where the picture really is (x0, y0, x1, y1): empty space around it does not bounce
float tri(float x){ return 1.0 - abs(1.0 - mod(x, 2.0)); }        // 0..1..0 ping-pong
vec3 hueRot(vec3 c, float a){ const vec3 k = vec3(0.57735); float ca = cos(a); return c * ca + cross(k, c) * sin(a) + k * dot(k, c) * (1.0 - ca); }
void main(){
  vec2 uv = vUV.st; float asp = ASP();
  float sp = d2(uP.x, 100.0), sz = uP.x - sp * 100.0, an = d2(uP.y, 100.0), cc = uP.y - an * 100.0;
  vec4 bb = (uBB.z - uBB.x > 0.01 && uBB.w - uBB.y > 0.01) ? uBB : vec4(0.0, 0.0, 1.0, 1.0);
  vec2 pw = bb.zw - bb.xy;                                             // the picture's own size (0-1 of the screen)
  float s = (0.08 + sz / 99.0 * 0.82) / max(pw.x, pw.y * 1.0);          // how big it flies around
  s = min(s, 0.98 / max(pw.x, pw.y));
  vec2 box = pw * s;                                                   // its size on screen
  float th = radians(20.0 + an / 99.0 * 50.0);                         // flight angle 20-70 degrees
  vec2 v = vec2(cos(th), sin(th) * asp) * (0.03 + sp / 99.0 * 0.5);
  vec2 room = max(vec2(1.0) - box, vec2(0.0001));
  float n = clamp(uP.z, 0.0, 12.0);                                    // corner hits so far: one more copy for each (counted by the engine)
  vec4 t = vec4(0.0);
  for (int k = 0; k < 13; k++) {
    if (float(k) > n) break;
    vec2 tt = (uTime + float(k) * 13.7) * v / room;                     // every copy flies the same path, at its own place on it
    vec2 pos = vec2(tri(tt.x), tri(tt.y)) * room;                      // bottom-left corner of the picture on screen
    if (uv.x < pos.x || uv.y < pos.y || uv.x > pos.x + box.x || uv.y > pos.y + box.y) continue;
    vec4 c = texA(bb.xy + (uv - pos) / s);
    if (cc > 0.5) c.rgb = max(hueRot(c.rgb, (floor(tt.x) + floor(tt.y) + float(k) * 3.0) * 2.39996), 0.0);   // a new colour on every bounce
    t = c + t * (1.0 - c.a);                                          // newest copies on top
  }
  fragColor = TDOutputSwizzle(mix(texture(sTD2DInputs[0], uv), t, uMix));
}
