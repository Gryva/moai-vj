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

// SPOT PULSE  one spot (a logo's globe, a face...) swells and flashes with the kick.
// uP.x = x * 100 + y (0-99, y from the top), uP.y = size * 100 + strength (0-99)
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float asp = ASP();
  float px = floor(uP.x / 100.0 + 0.001), py = uP.x - px * 100.0;
  float sz = floor(uP.y / 100.0 + 0.001), st = uP.y - sz * 100.0;
  vec2 c = vec2(px / 99.0, 1.0 - py / 99.0);
  float R = 0.03 + (sz / 99.0) * 0.6, s = st / 99.0 * 1.6;
  float beat = clamp(a.w * 0.9 + a.x * 0.35, 0.0, 1.5);
  vec2 d = (uv - c) * vec2(asp, 1.0); float r = length(d);
  float fall = smoothstep(R, 0.0, r);
  float k = s * beat * 0.42 * fall;
  vec2 uv2 = c + (uv - c) * (1.0 - k);                      // magnify around the spot
  vec3 col = tex(uv2) * (1.0 + s * beat * 0.7 * fall * fall);   // and a flash in its middle
  OUT(col);
}
