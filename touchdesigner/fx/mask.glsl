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
// MASK  show the layer only inside (or outside) a shape.
// uP.x = x * 100 + y (centre, 0-99, y from the top), uP.y = width * 100 + height, uP.z = shape * 1000 + invert * 100 + softness
void main(){
  vec2 uv = vUV.st; float asp = ASP();
  float px = d2(uP.x, 100.0), py = uP.x - px * 100.0, w = d2(uP.y, 100.0), h = uP.y - w * 100.0;
  float shp = d2(uP.z, 1000.0), inv = d2(uP.z - shp * 1000.0, 100.0), sf = uP.z - shp * 1000.0 - inv * 100.0;
  vec2 c = vec2(px / 99.0, 1.0 - py / 99.0);
  vec2 hs = vec2(0.01 + w / 99.0 * 0.6, 0.01 + h / 99.0 * 0.6);   // half size, in screen heights (so a circle stays round)
  vec2 q = (uv - c) * vec2(asp, 1.0) / hs;
  float d = shp < 0.5 ? length(q) : max(abs(q.x), abs(q.y));        // 0 circle / oval, 1 rectangle
  float f = 0.005 + sf / 99.0 * 0.6;
  float m = 1.0 - smoothstep(1.0 - f, 1.0 + f, d);
  if (inv > 0.5) m = 1.0 - m;
  vec4 t = texture(sTD2DInputs[0], uv);
  fragColor = TDOutputSwizzle(mix(t, t * m, uMix));
}
