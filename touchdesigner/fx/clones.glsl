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

float ASP(){ vec2 r = RES(); return r.x / r.y; }
vec2 mir(vec2 p){ return abs(fract(p * 0.5) * 2.0 - 1.0); }
#define OUT(c) fragColor = TDOutputSwizzle(outc(vUV.st, (c)))

// CLONES  copies of the layer: grid / row / column / fan, with or without overlap, each copy moving on its own.
// uP.x packs the choices: copies + 10 * overlap (0-2) + 100 * motion (0 still, 1 bob, 2 shake, 3 drift, 4 pulse, 5 spin) + 1000 * layout (0 grid, 1 row, 2 column, 3 fan)
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float asp = ASP();
  float p = floor(uP.x + 0.5);
  float n = mod(p, 10.0); if (n < 1.0) n = 3.0;
  float ovs = mod(floor(p / 10.0), 10.0), mot = mod(floor(p / 100.0), 10.0), lay = floor(p / 1000.0);
  float ov = ovs < 0.5 ? 0.0 : ovs < 1.5 ? 0.45 : 1.0;
  int cols = int(n); int rows = lay < 0.5 ? cols : 1; int total = cols * rows;
  float s = (1.0 + ov) / n;
  if (lay > 2.5) s = 0.5 + 0.2 * ov;
  vec3 acc = vec3(0.0); float aa = 0.0;
  for (int k = 0; k < 64; k++) {
    if (k >= total) break;
    float i = float(k - (k / cols) * cols), j = float(k / cols);
    vec2 c;
    if (lay < 0.5) c = vec2((i + 0.5) / n, 1.0 - (j + 0.5) / n);
    else if (lay < 1.5) c = vec2((i + 0.5) / n, 0.5);
    else if (lay < 2.5) c = vec2(0.5, 1.0 - (i + 0.5) / n);
    else c = vec2(0.5) + (i - (n - 1.0) * 0.5) * vec2(0.62, -0.18) / n * (1.25 - 0.5 * ov);
    float ph = hash(vec2(float(k) * 1.37, 4.2));
    vec2 off = vec2(0.0); float sc = s; float ang = 0.0;
    if (mot > 0.5 && mot < 1.5) off.y = sin(uTime * 2.2 + ph * 6.283) * 0.12 * s;
    else if (mot > 1.5 && mot < 2.5) { float f = floor(uTime * 14.0); off = (vec2(hash(vec2(float(k), f)), hash(vec2(f, float(k) + 9.0))) - 0.5) * 0.09 * s; }
    else if (mot > 2.5 && mot < 3.5) off = vec2(cos(uTime * 0.8 + ph * 6.283), sin(uTime * 0.8 + ph * 6.283)) * 0.12 * s;
    else if (mot > 3.5 && mot < 4.5) sc *= 1.0 + (a.w * 0.3 + a.x * 0.1) * (ph > 0.5 ? 1.0 : -0.5) + 0.04 * sin(uTime * 3.0 + ph * 6.283);
    else if (mot > 4.5) ang = uTime * 0.7 * (ph > 0.5 ? 1.0 : -1.0) + ph * 6.283;
    vec2 q = uv - c - off;
    if (ang != 0.0) { q.x *= asp; q = rot(ang) * q; q.x /= asp; }
    q = q / sc + 0.5;
    if (q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0) continue;
    vec4 t = texture(sTD2DInputs[0], q);
    acc = mix(acc, t.rgb, t.a); aa = t.a + aa * (1.0 - t.a);
  }
  vec4 o = texture(sTD2DInputs[0], uv);
  fragColor = TDOutputSwizzle(vec4(mix(o.rgb, acc, uMix), clamp(mix(o.a, aa, uMix), 0.0, 1.0)));
}
