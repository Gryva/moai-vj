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
// LINES  uP.x mode: 0 WAVES (stacked lines lifted by the image), 1 CONTOUR (iso lines), 2 HATCH (cross hatching), 3 SCAN (line halftone)
float band(float d, float w){ return 1.0 - smoothstep(w * 0.5, w * 0.5 + 0.0015, abs(d)); }
vec3 waves(vec2 uv, vec4 a){
  float rows = 46.0 + floor(a.y * 10.0);
  float amp = 0.07 + a.x * 0.09 + a.w * 0.04;
  float th = 0.0022 + a.z * 0.0018;
  float acc = 0.0;
  int k0 = int(floor((uv.y - amp - th) * rows)), k1 = int(floor((uv.y + th) * rows)) + 1;
  for (int k = k0; k <= k1; k++) {
    float y0 = (float(k) + 0.5) / rows;
    float l = luma(tex(vec2(uv.x, y0 + amp * 0.5)));
    float j = (vnoise(vec2(uv.x * 40.0, float(k) * 3.1 + uTime * 2.0)) - 0.5) * 0.01 * (0.5 + a.z);
    acc = max(acc, band(uv.y - (y0 + l * amp + j * l), th));
  }
  vec3 col = mix(vec3(1.0), hsv(fract(uv.y * 0.4 + uTime * 0.04), 0.7, 1.0), 0.35 + 0.3 * a.y);
  return col * acc * (1.0 + a.w * 0.6);
}
vec3 contour(vec2 uv, vec4 a){
  vec3 src = tex(uv); float l = luma(src);
  float lv = 9.0 + a.y * 8.0;
  float f = l * lv - uTime * 0.4 - a.w * 0.5;
  float d = abs(fract(f) - 0.5) / max(fwidth(f), 1e-4);
  float line = 1.0 - smoothstep(0.6, 1.6 + a.x * 1.5, d);
  vec3 col = hsv(fract(floor(f) * 0.13 + uTime * 0.03), 0.75, 1.0);
  return col * line * smoothstep(0.02, 0.08, l) * (1.0 + a.w * 0.5);
}
vec3 hatch(vec2 uv, vec4 a){
  vec2 p = uv * RES(); float l = luma(tex(uv)) * (1.0 + a.x * 0.5);
  float s = 7.0;
  float h1 = band(fract((p.x + p.y) / s) - 0.5, 0.3) * step(0.12, l);
  float h2 = band(fract((p.x - p.y) / s) - 0.5, 0.3) * step(0.35, l);
  float h3 = band(fract(p.y / (s * 0.75) + uTime * 0.2) - 0.5, 0.35) * step(0.6, l);
  float ink = max(h1, max(h2, h3));
  return mix(vec3(0.95, 0.92, 0.85), vec3(1.0, 0.35, 0.2), a.w * 0.6) * ink;
}
vec3 scan(vec2 uv, vec4 a){
  float rows = 110.0 - a.x * 30.0;
  float y = uv.y * rows; float cy = (floor(y) + 0.5) / rows;
  float shift = (vnoise(vec2(floor(y) * 0.7, uTime * 3.0)) - 0.5) * 0.04 * a.z;
  vec3 c = tex(vec2(uv.x + shift, cy));
  float w = clamp(luma(c) * 1.2, 0.0, 0.95);
  float on = 1.0 - smoothstep(w * 0.5, w * 0.5 + 0.06, abs(fract(y) - 0.5));
  return c * on * (1.3 + a.w * 0.6);
}
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  int m = int(floor(uP.x + 0.5));
  vec3 c = m == 0 ? waves(uv, a) : m == 1 ? contour(uv, a) : m == 2 ? hatch(uv, a) : scan(uv, a);
  if (uCA.w > 0.5) c = fxTint(c, uv) * max(c.r, max(c.g, c.b));
  fragColor = TDOutputSwizzle(vec4(mix(tex(uv), c, uMix), 1.0));
}
