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
  float kick = clamp(uAudio.w, 0.0, 1.0) * uP.w;                     // the beat only brightens and stretches a little - it never switches lines on/off (that was the flicker)
  vec2 d = vec2(cos(uP.y), sin(uP.y));
  vec2 du = d / vec2(asp, 1.0);
  vec2 pr = vec2(-d.y, d.x);
  vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  vec4 base = S4(uv);
  float L = (0.05 + 0.55 * sp) * (1.0 + 0.35 * kick);
  vec4 o = base;
  if (st >= 1) {
    vec4 acc = vec4(0.0); float wsum = 0.0;
    for (int i = 0; i < 24; i++) { float k = (float(i) + 0.5) / 24.0; float w = 1.0 - k * 0.85; acc += S4(uv + du * L * 0.45 * k) * w; wsum += w; }
    acc /= wsum;
    o = max(o, acc * 0.9);
  }
  if (st == 0 || st == 2) {                                         // LINES: soft anti-aliased streaks, steady from frame to frame
    float px = 1.0 / RES().y;
    float rowW = max(0.0045 + 0.004 * (1.0 - sp), px * 4.0);          // a row is never thinner than 4 pixels
    float c = dot(p, pr) / rowW, row = floor(c), fr = fract(c);
    float h = hash(vec2(row, 3.1)), h2 = hash(vec2(row, 7.7));
    float fw = max(fwidth(c), 1e-4);
    float lw = max(0.14, fw * 0.9);
    float thin = 1.0 - smoothstep(lw, lw + fw * 1.5, abs(fr - 0.5));  // anti-aliased line (no crawling jaggies)
    float lit = smoothstep(0.30 - 0.25 * sp, 0.36 - 0.25 * sp, h);     // which rows carry a line - fixed, not tied to the beat
    float s = dot(p, d);
    float run = fract(s * (1.5 + 3.0 * h2) + uTime * (0.35 + 1.2 * sp) * (0.6 + h));
    float fd = max(fwidth(run) * 1.5, 0.02);
    float dash = smoothstep(0.0, 0.08 + fd, run) * (1.0 - smoothstep(0.30, 0.55 + 0.35 * sp, run));
    vec4 src = vec4(0.0); float near = 0.0;                             // the colour behind: a soft weighted average (no hard jumps)
    for (int i = 1; i <= 16; i++) { float k = float(i) / 16.0; vec4 t = S4(uv + du * L * k); float w = (1.0 - k) * t.a; src += t * w; near = max(near, w); }
    float ws = src.a; src = ws > 1e-4 ? src / ws : vec4(0.0);
    float m = thin * lit * dash * near * (1.0 - base.a * 0.85) * (0.8 + 0.4 * kick);
    vec3 col = src.a > 0.001 ? src.rgb / max(src.a, 1e-3) : vec3(1.0);
    col = mix(clamp(col, 0.0, 1.0), vec3(1.0), 0.35);
    o = vec4(o.rgb + col * m * (1.0 - o.a * 0.5), max(o.a, m));
  }
  fragColor = TDOutputSwizzle(mix(base, o, uMix));
}
