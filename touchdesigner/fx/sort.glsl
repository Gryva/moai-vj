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

float ASP(){ vec2 r = RES(); return r.x / r.y; }
vec2 mir(vec2 p){ return abs(fract(p * 0.5) * 2.0 - 1.0); }
#define OUT(c) fragColor = TDOutputSwizzle(vec4(mix(tex(vUV.st), (c), uMix), 1.0))

// PIXEL SORT  bright runs smear downward into sorted-looking streaks. uP.x = amount, bass = streak length
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  vec3 base = tex(uv); float lb = luma(base);
  float thr = mix(0.85, 0.18, clamp(uP.x, 0.0, 1.0)) - a.x * 0.12;
  vec3 c = base;
  if (lb > thr) {
    float len = 0.05 + 0.3 * a.x + 0.12 * a.w;
    vec3 best = base; float lbest = lb; float run = 0.0;
    for (int i = 1; i <= 40; i++) {
      vec3 s = tex(uv + vec2(0.0, len * float(i) / 40.0));
      float ls = luma(s);
      if (ls < thr) break;
      run = float(i) / 40.0;
      if (ls > lbest) { best = s; lbest = ls; }
    }
    c = mix(base, best, 0.4 + 0.6 * run);
    c.r = mix(c.r, tex(uv + vec2(0.0, len * 0.08)).r, 0.5 * a.z);
  }
  OUT(c);
}
