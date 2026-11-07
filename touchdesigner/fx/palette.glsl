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

// COLOUR TINT  the image in one colour: black -> colour -> white. uP.x = colour index 0..7
vec3 col(int i){
  if (i == 0) return vec3(1.0, 0.13, 0.08);    // red
  if (i == 1) return vec3(1.0, 0.48, 0.05);    // orange
  if (i == 2) return vec3(1.0, 0.86, 0.1);     // yellow
  if (i == 3) return vec3(0.2, 1.0, 0.35);     // green
  if (i == 4) return vec3(0.1, 0.88, 1.0);     // cyan
  if (i == 5) return vec3(0.18, 0.35, 1.0);    // blue
  if (i == 6) return vec3(0.62, 0.22, 1.0);    // violet
  return vec3(1.0, 0.25, 0.7);                 // pink
}
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  vec3 k = fxTint(col(int(clamp(floor(uP.x + 0.5), 0.0, 7.0))), uv);
  float l = smoothstep(0.03, 0.85, luma(tex(uv)));
  float pivot = 0.62 - a.x * 0.1;                              // bass pushes more of the image to the bright end
  vec3 c = l < pivot ? k * (l / pivot) : mix(k, vec3(1.0), (l - pivot) / (1.0 - pivot) * 0.8);
  OUT(c);
}
