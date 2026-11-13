// NOISE SOURCE  a generated background: 8 kinds, colours, movement, warp, detail, reacting to the music.
// uN1 = (kind 0 smooth 1 clouds 2 ridges 3 cells 4 marble 5 waves 6 static 7 plasma, scale, speed, detail 1-8)
// uN2 = (warp, contrast, direction degrees, music)   uN3 = (colour mode 0 two 1 three 2 rainbow 3 mono, brightness, seed, steps 0 = smooth)
// uC1 / uC2 / uC3 = the colours (dark -> mid -> light)   uT.x = time   uA = audio (low, mid, high, kick)
uniform vec4 uT; uniform vec4 uA; uniform vec4 uN1; uniform vec4 uN2; uniform vec4 uN3; uniform vec4 uC1; uniform vec4 uC2; uniform vec4 uC3;
layout(location = 0) out vec4 fragColor;
float h1(vec2 p){ vec3 q = fract(vec3(p.xyx) * 0.1031 + uN3.z * 0.0173); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }   // stable hash: no blocky seams
vec2 h2(vec2 p){ vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973) + uN3.z * 0.0173); q += dot(q, q.yzx + 33.33); return fract((q.xx + q.yz) * q.zy); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h1(i), h1(i + vec2(1, 0)), f.x), mix(h1(i + vec2(0, 1)), h1(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p, int oc){ float v = 0.0, a = 0.5, n = 0.0; for (int i = 0; i < 8; i++) { if (i >= oc) break; v += a * vn(p); n += a; p = p * 2.03 + 11.7; a *= 0.5; } return v / n; }
float ridge(vec2 p, int oc){ float v = 0.0, a = 0.5, n = 0.0; for (int i = 0; i < 8; i++) { if (i >= oc) break; float r = 1.0 - abs(vn(p) * 2.0 - 1.0); v += a * r * r; n += a; p = p * 2.07 + 5.3; a *= 0.5; } return v / n; }
float cells(vec2 p, float t){ vec2 i = floor(p), f = fract(p); float d = 8.0;
  for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) { vec2 g = vec2(x, y), o = h2(i + g); o = 0.5 + 0.5 * sin(t + 6.2831 * o); d = min(d, length(g + o - f)); }
  return clamp(d, 0.0, 1.0); }
vec3 rainbow(float t){ return 0.5 + 0.5 * cos(6.2831 * (t + vec3(0.0, 0.33, 0.67))); }
void main(){
  vec2 uv = vUV.st; vec2 res = uTDOutputInfo.res.zw; float asp = res.x / res.y;
  int kind = int(uN1.x + 0.5); int oc = int(clamp(uN1.w, 1.0, 8.0) + 0.5);
  float mus = uN2.w, t = uT.x * uN1.z * (1.0 + uA.x * mus * 0.8);
  float an = radians(uN2.z); vec2 dir = vec2(cos(an), sin(an));
  vec2 p = (uv - 0.5) * vec2(asp, 1.0) * uN1.y * (1.0 - uA.w * mus * 0.06) + dir * t;
  if (uN2.x > 0.001) p += uN2.x * (vec2(fbm(p * 0.7 + t * 0.3, 4), fbm(p * 0.7 + 9.1 - t * 0.3, 4)) - 0.5) * 3.0;   // warp: the pattern swirls into itself
  float v;
  if (kind == 0) v = vn(p + t * 0.2);
  else if (kind == 1) v = fbm(p, oc);
  else if (kind == 2) v = ridge(p, oc);
  else if (kind == 3) v = cells(p, t * 2.0);
  else if (kind == 4) v = 0.5 + 0.5 * sin(p.x * 2.0 + fbm(p, oc) * 9.0);
  else if (kind == 5) v = 0.5 + 0.5 * sin((p.x * dir.x + p.y * dir.y) * 3.0 + fbm(p * 0.5, oc) * 4.0 - t * 3.0);
  else if (kind == 6) v = h1(floor(uv * res / max(1.0, 6.0 - uN1.y)) + floor(uT.x * 24.0));
  else v = 0.5 + 0.25 * (sin(p.x * 1.7 + t) + sin(p.y * 2.3 - t * 1.3) + sin((p.x + p.y) * 1.1 + t * 0.7) + sin(length(p) * 2.0 - t)) * 0.5;
  v = clamp((v - 0.5) * uN2.y + 0.5, 0.0, 1.0);                     // contrast
  if (uN3.w > 0.5) v = floor(v * uN3.w + 0.5) / uN3.w;              // steps: flat bands
  v = clamp(v + uA.w * mus * 0.15 * v, 0.0, 1.0);
  int cm = int(uN3.x + 0.5); vec3 c;
  if (cm == 0) c = mix(uC1.rgb, uC2.rgb, v);
  else if (cm == 1) c = v < 0.5 ? mix(uC1.rgb, uC2.rgb, v * 2.0) : mix(uC2.rgb, uC3.rgb, v * 2.0 - 1.0);
  else if (cm == 2) c = rainbow(v + t * 0.05) * (0.25 + 0.75 * v);
  else c = vec3(v);
  c *= uN3.y;
  fragColor = TDOutputSwizzle(vec4(clamp(c, 0.0, 1.0), 1.0));
}
