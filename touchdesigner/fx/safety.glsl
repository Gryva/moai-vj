uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
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

vec3 rgb2hsv(vec3 c){ vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0); vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g)); vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r)); float d = q.x - min(q.w, q.y); float e = 1.0e-10; return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x); }
float ASP(){ vec2 r = RES(); return r.x / r.y; }
#define OUT(c) fragColor = TDOutputSwizzle(vec4(mix(tex(vUV.st), (c), uMix), 1.0))

// FLASH SAFETY  input 1 = previous output. Limits how fast any pixel can change brightness.
// uP.x = safety 0..1  (0 = off, 1 = very gentle). Big jumps become quick fades; slow changes pass untouched.
void main(){
  vec3 cur = tex(vUV.st);
  vec3 prev = texture(sTD2DInputs[1], vUV.st).rgb;
  float s = clamp(uP.x, 0.0, 1.0);
  float maxd = mix(1.0, 0.035, s * s * (3.0 - 2.0 * s));          // per-frame step limit
  float lc = luma(cur), lp = luma(prev), dl = lc - lp;
  float lim = clamp(dl, -maxd, maxd);                                // limit brightness change...
  vec3 outc = cur * ((lp + lim + 1e-4) / (lc + 1e-4));               // ...but keep the new colours / motion
  outc = mix(outc, prev + clamp(cur - prev, -maxd * 1.5, maxd * 1.5), 0.35 * s);   // tame colour flips too
  fragColor = TDOutputSwizzle(vec4(mix(cur, clamp(outc, 0.0, 1.0), uMix), 1.0));
}
