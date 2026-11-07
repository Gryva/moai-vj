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

vec3 pal(float t){ t = clamp(t, 0.0, 1.0);
  vec3 c = mix(vec3(0.0, 0.0, 0.08), vec3(0.25, 0.0, 0.6), smoothstep(0.0, 0.25, t));
  c = mix(c, vec3(0.95, 0.0, 0.45), smoothstep(0.25, 0.5, t));
  c = mix(c, vec3(1.0, 0.5, 0.0), smoothstep(0.5, 0.75, t));
  return mix(c, vec3(1.0, 1.0, 0.85), smoothstep(0.75, 1.0, t)); }
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  uv.x += sin(uv.y * 30.0 + uTime * 3.0) * 0.003 * (1.0 + a.x * 4.0);
  float l = luma(tex(uv));
  float bl = 0.0; for(int i = -2; i <= 2; i++) for(int j = -2; j <= 2; j++) bl += luma(tex(uv + vec2(i, j) * PX() * 2.0));
  l = mix(l, bl / 25.0, 0.5);
  l = l * (0.95 + a.x * 0.8) + a.w * 0.15 + (vnoise(uv * 8.0 + uTime) - 0.5) * 0.06;
  vec3 c = pal(l);
  if (uCA.w > 0.5) { float k = clamp(l, 0.0, 1.0); c = int(uCA.w + 0.5) == 1 ? uCA.rgb * (0.08 + k * 1.3) : mix(uCA.rgb, uCB.rgb, k) * (0.35 + k * 0.9); }
  c *= 0.9 + 0.1 * sin(vUV.t * RES().y * 0.8);
  fragColor = TDOutputSwizzle(outc(vUV.st, c));
}