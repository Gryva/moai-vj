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

float character(int n, vec2 q){
  q = floor(q * vec2(4.0, -4.0) + 2.5);
  if(clamp(q.x, 0.0, 4.0) == q.x && clamp(q.y, 0.0, 4.0) == q.y){
    int b = int(round(q.x) + 5.0 * round(q.y));
    if(((n >> b) & 1) == 1) return 1.0; }
  return 0.0; }
void main(){
  vec4 a = uAudio; vec2 frag = vUV.st * RES();
  float cs = 8.0;
  vec3 c = tex(floor(frag / cs) * cs / RES());
  float g = luma(c) * (1.0 + a.x * 0.8);
  int n = 0;
  if(g > 0.05) n = 4096; if(g > 0.2) n = 65600; if(g > 0.3) n = 332772; if(g > 0.4) n = 15255086;
  if(g > 0.5) n = 23385164; if(g > 0.6) n = 15252014; if(g > 0.7) n = 13199452; if(g > 0.8) n = 11512810;
  vec2 q = mod(frag / 4.0, 2.0) - vec2(1.0);
  float rain = fract(floor(frag.x / cs) * 0.137 + uTime * (0.2 + a.y));
  vec3 green = mix(fxTint(vec3(0.1, 1.0, 0.35), vUV.st), vec3(0.9, 1.0, 0.9), a.w * (uCA.w > 0.5 ? 0.3 : 1.0));
  vec3 o = green * character(n, q) * (0.55 + 0.45 * rain + a.z * 0.5);
  fragColor = TDOutputSwizzle(outc(vUV.st, o));
}