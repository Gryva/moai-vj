uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
layout(location = 0) out vec4 fragColor;
// effect colour from the phone: uCA = (colour A, mode 0 own colour / 1 solid / 2 linear / 3 radial), uCB = (colour B, angle)
uniform vec4 uCA;
uniform vec4 uCB;
vec3 fxTint(vec3 def, vec2 uv){
  int m = int(uCA.w + 0.5);
  if (m == 0) return def;
  if (m == 1) return uCA.rgb;
  vec2 r = uTD2DInfos[0].res.zw; vec2 q = (uv - 0.5) * vec2(r.x / max(1.0, r.y), 1.0);
  if (m == 2) { vec2 d = vec2(cos(uCB.w), sin(uCB.w)); float t = clamp(dot(q, d) / (0.5 * (abs(d.x) * r.x / max(1.0, r.y) + abs(d.y))) * 0.5 + 0.5, 0.0, 1.0); return mix(uCA.rgb, uCB.rgb, t); }
  return mix(uCA.rgb, uCB.rgb, clamp(length(q) * 1.25, 0.0, 1.0));
}
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

// TUNNEL FLIGHT  image wrapped on the walls of an endless tube. uP.x = flight speed, kick = surge
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float asp = ASP();
  vec2 q = uv - 0.5; q.x *= asp;
  float r = max(length(q), 1e-3);
  float ang = atan(q.y, q.x) + uTime * 0.08 + a.y * 0.15;
  float spd = 0.15 + clamp(uP.x, 0.0, 1.0) * 1.4;
  float depth = 0.32 / r + uTime * spd + a.w * 0.35;
  vec2 tuv = mir(vec2(ang / 3.14159265 * 2.0, depth));
  vec3 wall = tex(0.5 + (tuv - 0.5) * vec2(0.55, 0.8)) * 1.3;   // sample the busy middle of the frame
  float ring = smoothstep(0.92, 1.0, fract(depth * 1.5)) * (0.3 + a.x * 1.2);
  wall += ring * fxTint(hsv(fract(depth * 0.1 + uTime * 0.03), 0.6, 1.0), uv) * 0.5;
  wall *= smoothstep(0.02, 0.35, r);                       // fog toward the vanishing point
  float hole = smoothstep(0.22, 0.10, r);                  // the source still visible at the far end
  vec3 core = tex((uv - 0.5) * (1.6 - a.x * 0.3) + 0.5) * hole;
  OUT(wall * (1.0 - hole) + core);
}
