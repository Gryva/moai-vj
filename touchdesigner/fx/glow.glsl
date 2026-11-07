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
  vec4 a = uAudio; vec2 uv = vUV.st; vec2 px = PX();
  vec3 base = tex(uv); vec3 glow = vec3(0.0);
  for(int r = 1; r <= 6; r++){ for(int k = 0; k < 8; k++){
    float ang = float(k) * 0.785398 + float(r);
    glow += tex(uv + vec2(cos(ang), sin(ang)) * px * float(r) * (3.0 + a.x * 4.0)) / float(r); } }
  glow /= 18.0;
  vec3 tint = fxTint(mix(vec3(0.15, 0.85, 1.0), vec3(1.0, 0.25, 0.75), clamp(uv.y + 0.4 * sin(uTime * 0.5) + a.z * 0.5, 0.0, 1.0)), uv);
  vec3 c = base * mix(vec3(1.0), tint, 0.5) + glow * tint * (1.4 + a.x * 2.5) + a.w * 0.12 * tint;
  c *= 1.0 - 0.6 * length(uv - 0.5);
  fragColor = TDOutputSwizzle(vec4(mix(tex(vUV.st), c, uMix), 1.0));
}