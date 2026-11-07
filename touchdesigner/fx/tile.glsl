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

// TILE  mirrored repeats of the frame, tiles pulse on the kick in a checkerboard. uP.x = tiles per side
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  float n = max(1.0, floor(uP.x + 0.5));
  vec2 g = uv * n; vec2 id = floor(g); vec2 f = fract(g);
  if (mod(id.x, 2.0) > 0.5) f.x = 1.0 - f.x;
  if (mod(id.y, 2.0) > 0.5) f.y = 1.0 - f.y;
  float ph = mod(id.x + id.y, 2.0) * 2.0 - 1.0;
  float z = 1.0 - a.w * 0.12 * ph - a.x * 0.05;
  vec3 c = tex((f - 0.5) * z + 0.5);
  float pick = step(0.75, hash(id + floor(uTime * 2.0)));
  c *= 1.0 + a.w * 0.5 * pick;
  c *= 1.0 - 0.25 * smoothstep(0.46, 0.5, max(abs(f.x - 0.5), abs(f.y - 0.5))) * (1.0 - a.z);
  OUT(c);
}
