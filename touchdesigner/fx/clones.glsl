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

// CLONES  copies of the layer: grid / row / column / fan / pile, with or without overlap, each copy moving on its own.
// uP.x packs: count digit + 10 * overlap (0-2) + 100 * motion (0 still, 1 bob, 2 shake, 3 drift, 4 pulse, 5 spin)
//             + 1000 * layout (0 grid, 1 row, 2 column, 3 fan, 4 pile) + 10000 * random (0 none, 1 tilt, 2 flip, 3 tilt + flip)
//             + 100000 * copy size (0 normal, 1 0.5, 2 0.7, 3 0.85, 4 1.2, 5 1.5, 6 2)
// count digit: 2-6 and 8 as is, 9 = 10, 7 = 12, 1 = 16, 0 = 24
uniform vec4 uBB;   // where the picture really is (x0, y0, x1, y1), measured by the engine: empty space around it is not copied
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float asp = ASP();
  float p = floor(uP.x + 0.5);
  float d = mod(p, 10.0);
  float n = d < 0.5 ? 24.0 : d < 1.5 ? 16.0 : d > 8.5 ? 10.0 : (d > 6.5 && d < 7.5) ? 12.0 : d;
  float ovs = mod(floor(p / 10.0), 10.0), mot = mod(floor(p / 100.0), 10.0), lay = mod(floor(p / 1000.0), 10.0), rnd = mod(floor(p / 10000.0), 10.0), szd = floor(p / 100000.0);
  float szk = szd < 0.5 ? 1.0 : szd < 1.5 ? 0.5 : szd < 2.5 ? 0.7 : szd < 3.5 ? 0.85 : szd < 4.5 ? 1.2 : szd < 5.5 ? 1.5 : 2.0;
  vec4 bb = (uBB.z - uBB.x > 0.01 && uBB.w - uBB.y > 0.01) ? uBB : vec4(0.0, 0.0, 1.0, 1.0);
  vec2 bs = bb.zw - bb.xy;                                           // the picture's own size inside the frame
  float hk = bs.y / bs.x;                                            // copy height / width, in screen units
  float ov = ovs < 0.5 ? 0.0 : ovs < 1.5 ? 0.45 : 1.0;
  float cols = lay < 0.5 ? (n <= 8.0 ? n : ceil(sqrt(n * asp))) : n;     // big counts: a grid of about n copies
  float rows = lay < 0.5 ? (n <= 8.0 ? n : ceil(n / cols)) : 1.0;
  int total = lay > 3.5 ? int(n) : int(cols * rows);
  float s = (1.0 + ov) / cols;
  if (lay < 0.5 && n > 8.0) s = (1.0 + ov) / max(cols, rows * asp);
  if (lay > 2.5 && lay < 3.5) s = 0.5 + 0.2 * ov;
  if (lay > 3.5) s = (1.1 + 0.9 * ov) * 1.25 / sqrt(n);                  // pile: copies big enough to cover and overlap
  s *= szk;
  float op4 = texture(sTD2DInputs[0], vec2(0.02)).a * texture(sTD2DInputs[0], vec2(0.98)).a * texture(sTD2DInputs[0], vec2(0.02, 0.98)).a * texture(sTD2DInputs[0], vec2(0.98, 0.02)).a;
  bool solid = op4 > 0.99;                                           // whole picture (no see-through): black counts as empty
  vec3 acc = vec3(0.0); float aa = 0.0;
  for (int k = 0; k < 64; k++) {
    if (k >= total) break;
    float fk = float(k);
    float i = mod(fk, cols), j = floor(fk / cols);
    vec2 c;
    if (lay < 0.5) c = vec2((i + 0.5) / cols, 1.0 - (j + 0.5) / rows);
    else if (lay < 1.5) c = vec2((i + 0.5) / n, 0.5);
    else if (lay < 2.5) c = vec2(0.5, 1.0 - (i + 0.5) / n);
    else if (lay < 3.5) c = vec2(0.5) + (i - (n - 1.0) * 0.5) * vec2(0.62, -0.18) / n * (1.25 - 0.5 * ov);
    else {                                                            // pile: a jittered grid, so the screen is covered without gaps
      float pc = ceil(sqrt(n * asp)), pr = ceil(n / pc);
      vec2 cell = vec2(mod(fk, pc), floor(fk / pc));
      c = (cell + 0.5 + (vec2(hash(vec2(fk, 2.1)), hash(vec2(fk, 5.3))) - 0.5) * 0.9) / vec2(pc, pr);
      c.y = 1.0 - c.y;
    }
    float ph = hash(vec2(fk * 1.37, 4.2));
    vec2 off = vec2(0.0); float sc = s; float ang = 0.0;
    if (rnd > 0.5 && rnd < 1.5 || rnd > 2.5) ang = (hash(vec2(fk, 11.7)) - 0.5) * 1.4;      // tilted: up to about 40 degrees either way
    bool fl = (rnd > 1.5) && hash(vec2(fk, 23.1)) > 0.5;                                     // some copies turned around
    if (mot > 0.5 && mot < 1.5) off.y = sin(uTime * 2.2 + ph * 6.283) * 0.12 * s;
    else if (mot > 1.5 && mot < 2.5) { float f = floor(uTime * 14.0); off = (vec2(hash(vec2(fk, f)), hash(vec2(f, fk + 9.0))) - 0.5) * 0.09 * s; }
    else if (mot > 2.5 && mot < 3.5) off = vec2(cos(uTime * 0.8 + ph * 6.283), sin(uTime * 0.8 + ph * 6.283)) * 0.12 * s;
    else if (mot > 3.5 && mot < 4.5) sc *= 1.0 + (a.w * 0.3 + a.x * 0.1) * (ph > 0.5 ? 1.0 : -0.5) + 0.04 * sin(uTime * 3.0 + ph * 6.283);
    else if (mot > 4.5) ang += uTime * 0.7 * (ph > 0.5 ? 1.0 : -1.0) + ph * 6.283;
    vec2 q = uv - c - off;
    if (ang != 0.0) { q.x *= asp; q = rot(ang) * q; q.x /= asp; }
    q = q / vec2(sc, sc * hk);                                        // each copy is the picture, not the whole frame
    if (fl) q.x = -q.x;
    q += 0.5;
    if (q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0) continue;
    vec4 t = texture(sTD2DInputs[0], bb.xy + q * bs);
    if (solid) t.a = smoothstep(0.02, 0.09, max(t.r, max(t.g, t.b)));
    acc = mix(acc, t.rgb, t.a); aa = t.a + aa * (1.0 - t.a);
  }
  vec4 o = texture(sTD2DInputs[0], uv);
  fragColor = TDOutputSwizzle(vec4(mix(o.rgb, acc, uMix), clamp(mix(o.a, aa, uMix), 0.0, 1.0)));
}
