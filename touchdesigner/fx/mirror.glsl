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

// SYMMETRY  uP.x mode: 0 left|right  1 top|bottom  2 four-way  3 radial
// uP.x packs: mode (0 left|right, 1 top|bottom, 2 quad, 3 radial) + 10 * side kept (0 left / top, 1 right / bottom) + 100 * line position (0-99, 50 = middle)
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float p = floor(uP.x + 0.5);
  int m = int(mod(p, 10.0)); bool flip = mod(floor(p / 10.0), 10.0) > 0.5;
  float ln = p >= 100.0 ? clamp(floor(p / 100.0) / 100.0, 0.02, 0.98) : 0.5;
  float w = sin(uTime * 0.6) * 0.03 * a.y;                       // the mirror line breathes with the mids
  float c = ln + w;
  if (m == 0) uv.x = flip ? c + abs(uv.x - c) : c - abs(uv.x - c);
  else if (m == 1) uv.y = flip ? c - abs(uv.y - c) : c + abs(uv.y - c);
  else if (m == 2) { uv.x = flip ? c + abs(uv.x - c) : c - abs(uv.x - c); uv.y = flip ? c - abs(uv.y - c) : c + abs(uv.y - c); }
  else {
    vec2 q = uv - 0.5; q.x *= ASP();
    float n = 2.0 + floor(ln * 10.0);                            // radial: the line position picks the number of slices
    float r = length(q), ang = atan(q.y, q.x) + uTime * 0.1 * (flip ? -1.0 : 1.0), seg = 6.2831853 / n;
    ang = abs(mod(ang, seg) - seg * 0.5); q = vec2(cos(ang), sin(ang)) * r; q.x /= ASP(); uv = q + 0.5;
  }
  OUT(tex(uv));
}
