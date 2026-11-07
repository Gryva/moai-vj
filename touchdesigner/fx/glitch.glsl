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

void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float t = floor(uTime * (10.0 + a.z * 20.0));
  float row = floor(uv.y * 28.0);
  float tear = step(0.8 - a.y * 0.3, hash(vec2(row, t))) * (hash(vec2(t, row + 3.0)) - 0.5) * (0.15 + a.x * 0.3);
  float burst = max(step(0.85, hash(vec2(floor(uTime * 3.0), 7.0))), step(0.5, a.w));
  vec2 blk = floor(uv * vec2(18.0, 10.0));
  uv.x += tear + burst * step(0.7, hash(blk + t)) * (hash(blk * 1.7 + t) - 0.5) * 0.2;
  float s = 0.004 + burst * 0.025 + abs(tear) * 0.25 + a.z * 0.02;
  vec3 c = vec3(tex(uv + vec2(s, 0)).r, tex(uv).g, tex(uv - vec2(s, 0)).b);
  c *= 0.82 + 0.18 * sin(vUV.t * RES().y * 1.6);
  // (inverted blocks removed: they flashed as white squares)
  c += step(0.986 - a.z * 0.03, hash(vec2(floor(vUV.t * 220.0), t))) * fxTint(vec3(0.9, 0.1, 0.6), vUV.st);
  fragColor = TDOutputSwizzle(vec4(mix(tex(vUV.st), c, uMix), 1.0));
}