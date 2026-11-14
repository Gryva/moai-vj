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

// CLONES  copies of the layer, spread over the screen. uP.x = count (1-150) + 256 * layout (0 grid, 1 row, 2 column, 3 fan, 4 scatter)
//   + 2048 * overlap (0-2) + 8192 * angle bits; uP.z = row / column scroll speed (0-31) (1 tilt, 2 flip).  uP.y = motion bits (1 bob, 2 shake, 4 drift, 8 pulse, 16 spin)
//   + 32 * size bits (0.5, 0.7, 0.85, 1, 1.2, 1.5, 2): each copy picks one of the chosen motions and one of the chosen sizes.
uniform vec4 uBB;   // where the picture really is (x0, y0, x1, y1), measured by the engine: empty space around it is not copied
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
float pickBit(float mask, float r, float nbits){                 // a random one of the set bits -> its index (-1 if none)
  float cnt = 0.0;
  for (int b = 0; b < 7; b++) { if (float(b) >= nbits) break; if (mod(floor(mask / exp2(float(b))), 2.0) > 0.5) cnt += 1.0; }
  if (cnt < 0.5) return -1.0;
  float want = floor(r * cnt), seen = 0.0;
  for (int b = 0; b < 7; b++) { if (float(b) >= nbits) break; if (mod(floor(mask / exp2(float(b))), 2.0) > 0.5) { if (seen == want) return float(b); seen += 1.0; } }
  return -1.0;
}
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float asp = ASP();
  float x = floor(uP.x + 0.5), y = floor(uP.y + 0.5);
  float n = clamp(mod(x, 256.0), 1.0, 150.0), lay = mod(floor(x / 256.0), 8.0), ovs = mod(floor(x / 2048.0), 4.0), rnd = mod(floor(x / 8192.0), 4.0);
  float motm = mod(y, 32.0), szm = mod(floor(y / 32.0), 128.0); if (szm < 0.5) szm = 8.0;
  float ov = ovs < 0.5 ? 0.0 : ovs < 1.5 ? 0.45 : 1.0;
  vec4 bb = (uBB.z - uBB.x > 0.01 && uBB.w - uBB.y > 0.01) ? uBB : vec4(0.0, 0.0, 1.0, 1.0);
  vec2 bs = bb.zw - bb.xy; float hk = bs.y / bs.x;
  float op4 = texture(sTD2DInputs[0], vec2(0.02)).a * texture(sTD2DInputs[0], vec2(0.98)).a * texture(sTD2DInputs[0], vec2(0.02, 0.98)).a * texture(sTD2DInputs[0], vec2(0.98, 0.02)).a;
  bool solid = op4 > 0.99;                                           // whole picture (no see-through): black counts as empty
  float cols = ceil(sqrt(n * asp)), rows = ceil(n / cols);
  float s;
  if (lay < 0.5) s = min(1.0 / cols, 1.0 / (rows * hk));
  else if (lay < 1.5) s = min(1.0 / n, 1.0 / hk);
  else if (lay < 2.5) s = min(1.0, 1.0 / (n * hk));
  else if (lay < 3.5) s = 0.5 / (1.0 + 0.0 * n);
  else s = min(1.0 / cols, 1.0 / (rows * hk)) * 1.15;
  s *= 1.0 + ov;
  vec3 acc = vec3(0.0); float aa = 0.0;
  float scr = uP.z / 31.0 * 0.25;                                   // ROW / COLUMN scroll (screens a second)
  if (scr > 0.0 && lay > 0.5 && lay < 1.5) uv.x = fract(uv.x - uTime * scr);
  if (scr > 0.0 && lay > 1.5 && lay < 2.5) uv.y = fract(uv.y + uTime * scr);
  for (int k = 0; k < 150; k++) {
    float fk = float(k);
    if (fk >= n) break;
    vec2 c;
    if (lay < 0.5) { float i = mod(fk, cols), j = floor(fk / cols); c = vec2((i + 0.5) / cols, 1.0 - (j + 0.5) / rows); }
    else if (lay < 1.5) c = vec2((fk + 0.5) / n, 0.5);
    else if (lay < 2.5) c = vec2(0.5, 1.0 - (fk + 0.5) / n);
    else if (lay < 3.5) c = vec2(0.5) + (fk - (n - 1.0) * 0.5) * vec2(0.62, -0.18) / n * (1.25 - 0.5 * ov);
    else {                                                            // scatter: evenly spread but not in rows (R2 sequence + a nudge)
      c = fract(vec2(0.5) + (fk + 1.0) * vec2(0.7548776662, 0.5698402910));
      c += (vec2(hash(vec2(fk, 2.1)), hash(vec2(fk, 5.3))) - 0.5) * 0.35 / vec2(cols, rows);
      c = c * 1.06 - 0.03;
    }
    float ph = hash(vec2(fk * 1.37, 4.2));
    float sb = pickBit(szm, hash(vec2(fk, 31.7)), 7.0);
    float sc = s * (sb < 0.5 ? 0.5 : sb < 1.5 ? 0.7 : sb < 2.5 ? 0.85 : sb < 3.5 ? 1.0 : sb < 4.5 ? 1.2 : sb < 5.5 ? 1.5 : 2.0);
    float mb = pickBit(motm, hash(vec2(fk, 47.3)), 5.0);
    vec2 off = vec2(0.0); float ang = 0.0;
    if (mod(rnd, 2.0) > 0.5) ang = (hash(vec2(fk, 11.7)) - 0.5) * 1.4;                 // tilted: up to about 40 degrees either way
    bool fl = rnd > 1.5 && hash(vec2(fk, 23.1)) > 0.5;                                    // some copies turned around
    if (mb > -0.5 && mb < 0.5) off.y = sin(uTime * 2.2 + ph * 6.283) * 0.12 * sc;                                   // bob
    else if (mb > 0.5 && mb < 1.5) { float f = floor(uTime * 14.0); off = (vec2(hash(vec2(fk, f)), hash(vec2(f, fk + 9.0))) - 0.5) * 0.09 * sc; }   // shake
    else if (mb > 1.5 && mb < 2.5) off = vec2(cos(uTime * 0.8 + ph * 6.283), sin(uTime * 0.8 + ph * 6.283)) * 0.12 * sc;   // drift
    else if (mb > 2.5 && mb < 3.5) sc *= 1.0 + (a.w * 0.3 + a.x * 0.1) * (ph > 0.5 ? 1.0 : -0.5) + 0.04 * sin(uTime * 3.0 + ph * 6.283);   // pulse
    else if (mb > 3.5) ang += uTime * 0.7 * (ph > 0.5 ? 1.0 : -1.0) + ph * 6.283;                                    // spin
    vec2 q = uv - c - off;
    float rr = max(sc, sc * hk) * 1.6 * max(1.0, asp);
    if (abs(q.x) > rr || abs(q.y) > rr) continue;                                       // far away: skip quickly
    if (ang != 0.0) { q.x *= asp; q = rot(ang) * q; q.x /= asp; }
    q = q / vec2(sc, sc * hk);
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
