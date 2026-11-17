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

// SPEED  makes a still object look like it's racing: streaks and / or motion blur trail behind it.
// uP.x = style (0 lines / 1 blur / 2 both), uP.y = direction of travel (radians, 0 = right, pi/2 = up), uP.z = speed 0..1, uP.w = beat boost 0..1
vec4 S4(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)) * step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0); }
void main(){
  vec2 uv = vUV.st; float asp = ASP();
  int st = int(uP.x + 0.5); float sp = clamp(uP.z, 0.0, 1.0);
  float kick = uAudio.w * uP.w;
  vec2 d = vec2(cos(uP.y), sin(uP.y));                             // where the object is going (screen space, aspect-correct)
  vec2 du = d / vec2(asp, 1.0);                                     // the same direction in texture units
  vec2 pr = vec2(-d.y, d.x);
  vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  vec4 base = S4(uv);
  float L = (0.05 + 0.55 * sp) * (1.0 + 1.2 * kick);                 // how far behind the trail reaches
  vec4 o = base;
  if (st >= 1) {                                                    // BLUR: the object smeared along its path
    vec4 acc = vec4(0.0); float wsum = 0.0;
    for (int i = 0; i < 18; i++) { float k = float(i) / 17.0; float w = 1.0 - k * 0.85; acc += S4(uv + du * L * 0.45 * k) * w; wsum += w; }
    acc /= wsum;
    o = max(o, acc * 0.9);
  }
  if (st == 0 || st == 2) {                                         // LINES: thin streaks pulled out of the object, rushing backwards
    float rowW = 0.0045 + 0.004 * (1.0 - sp);
    float c = dot(p, pr) / rowW, row = floor(c), fr = fract(c);
    float h = hash(vec2(row, 3.1)), h2 = hash(vec2(row, 7.7));
    float thin = smoothstep(0.5, 0.15, abs(fr - 0.5));               // a hairline in the middle of each row
    float lit = step(0.35 - 0.25 * sp - 0.2 * kick, h);              // not every row carries a line
    float s = dot(p, d);
    float run = fract(s * (2.0 + 5.0 * h2) + uTime * (0.6 + 2.6 * sp) * (0.6 + h));   // dashes flying backwards
    float dash = smoothstep(0.0, 0.08, run) * smoothstep(0.55 + 0.35 * sp, 0.3, run);
    vec4 src = vec4(0.0); float near = 0.0;
    for (int i = 1; i <= 16; i++) { float k = float(i) / 16.0; vec4 t = S4(uv + du * L * k); float w = (1.0 - k) * t.a;
      if (w > near) { near = w; src = t; } }
    float m = thin * lit * dash * near * (1.0 - base.a * 0.85);
    vec3 col = src.a > 0.001 ? src.rgb / src.a : vec3(1.0);
    col = mix(col, vec3(1.0), 0.35);                                  // a touch brighter than the body, like light streaks
    o = vec4(o.rgb + col * m * (1.0 - o.a * 0.5), max(o.a, m));
  }
  fragColor = TDOutputSwizzle(mix(base, o, uMix));
}
