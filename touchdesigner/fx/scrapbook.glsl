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

float ASP(){ vec2 r = RES(); return r.x / r.y; }
vec2 mir(vec2 p){ return abs(fract(p * 0.5) * 2.0 - 1.0); }
#define OUT(c) fragColor = TDOutputSwizzle(outc(vUV.st, (c)))

// SCRAPBOOK  paper cut-out collage: flat colours, white torn-paper edge with a shadow, paper grain, stop-motion wobble. uP.x = roughness
vec3 flat3(vec2 p){ vec2 d = PX() * 4.0;                          // soften first, so pieces are big flat shapes and not speckle
  vec3 c = (tex(p) * 2.0 + tex(p + vec2(d.x, 0.0)) + tex(p - vec2(d.x, 0.0)) + tex(p + vec2(0.0, d.y)) + tex(p - vec2(0.0, d.y))) / 6.0;
  vec3 q = floor(sqrt(max(c, 0.0)) * 3.0 + 0.5) / 3.0; return mix(vec3(luma(q)), q, 1.4); }
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float r = clamp(uP.x, 0.0, 1.0);
  float fr = floor(uTime * 8.0);                                   // moves 8 times a second, like stop motion
  vec2 jit = (vec2(hash(vec2(fr, 1.0)), hash(vec2(fr, 7.0))) - 0.5) * 0.006 * (0.4 + r);
  vec2 wob = (vec2(vnoise(uv * 9.0 + fr), vnoise(uv * 9.0 + 31.0 + fr)) - 0.5) * 0.014 * r;   // scissor-cut edges
  vec2 p = uv + jit + wob;
  vec3 q = flat3(p);
  vec2 px = PX() * (1.5 + 2.0 * r);
  float e = 0.0;
  e = max(e, length(flat3(p + vec2(px.x, 0.0)) - q)); e = max(e, length(flat3(p - vec2(px.x, 0.0)) - q));
  e = max(e, length(flat3(p + vec2(0.0, px.y)) - q)); e = max(e, length(flat3(p - vec2(0.0, px.y)) - q));
  float edge = smoothstep(0.3, 0.45, e);
  float sh = smoothstep(0.3, 0.45, length(flat3(p + vec2(-2.5, 2.5) * px) - q));
  q *= 1.0 - 0.28 * sh;                                            // each piece throws a small shadow
  q = mix(q, vec3(0.96, 0.94, 0.88), edge);                        // white paper edge
  q *= 0.88 + 0.24 * fbm(uv * RES() / 3.0);                        // paper grain
  q += (hash(uv * RES() + fr) - 0.5) * 0.05;
  q *= 1.0 + a.w * 0.15;
  OUT(clamp(q, 0.0, 1.0));
}
