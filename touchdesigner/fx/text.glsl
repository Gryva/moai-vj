uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
layout(location = 0) out vec4 fragColor;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int i=0;i<5;i++){ v += a*vnoise(p); p *= 2.03; a *= 0.5; } return v; }
// uM = (morph 0 old -> 1 new, scene dim under the text during a preset dip, morph active, unused)
uniform vec4 uM;
// text colour gradient: uTA = (colour A, mode 0 named colour / 1 solid / 2 ramp / 3 radial), uTB = (colour B, angle)
uniform vec4 uTA;
uniform vec4 uTB;
uniform vec4 uTR;                                                     // where the letters are (x0, y0, x1, y1): the ramp spans the words
vec3 tTint(vec2 q){
  int m = int(uTA.w + 0.5);
  if (m <= 1) return uTA.rgb;
  vec2 sz = max(uTR.zw - uTR.xy, vec2(0.01));
  vec2 p = (q - uTR.xy) / sz;                                         // 0..1 across the text block
  float as = sz.x * uTD2DInfos[1].res.z / max(1.0, sz.y * uTD2DInfos[1].res.w);
  vec2 c = (p - 0.5) * vec2(as, 1.0);
  if (m == 2) { vec2 d = vec2(cos(uTB.w), sin(uTB.w)); float t = clamp(dot(c, d) / (0.5 * (abs(d.x) * as + abs(d.y))) * 0.5 + 0.5, 0.0, 1.0); return mix(uTA.rgb, uTB.rgb, t); }
  return mix(uTA.rgb, uTB.rgb, clamp(length(c) / (0.5 * length(vec2(as, 1.0))), 0.0, 1.0));
}
vec3 tex(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)).rgb * (1.0 - uM.y); }
float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 hsv(float h, float s, float v){ vec3 k = clamp(abs(mod(h*6.0 + vec3(0,4,2), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1.0), k, s); }
vec2 PX(){ return uTD2DInfos[0].res.xy; }
vec2 RES(){ return uTD2DInfos[0].res.zw; }

// TEXT  input0 = scene, input1 = rendered text (white on transparent)
// uP = (mode, anim, speed, react)   uC = (r, g, b, glow)   uQ = (scale, tile density, outline, beat words flash)
// mode: 0 overlay 1 mask 2 cutout 3 invert 4 outline 5 glitch 6 refract
// anim: 0 static 1 beat pulse 2 wave 3 scroll 4 tile
uniform vec4 uC;
uniform vec4 uQ;
float gW = 1.0;                                                       // per-pixel morph weight (old -> new)
vec2 gD = vec2(0.0);                                                  // letter drift while morphing
float T(vec2 p){
  if (uM.z < 0.5) return texture(sTD2DInputs[1], p).a;
  float o = texture(sTD2DInputs[2], p + gD * gW).a;                   // old letters drift away as they dissolve
  float n = texture(sTD2DInputs[1], p - gD * (1.0 - gW)).a;           // new letters drift in from the other side
  return mix(o, n, gW);
}
uniform vec4 uX;   // x, y = move (-1..1), z = direction (0 across, 1 stacked letters, 2 sideways up, 3 sideways down), w = animation direction (0 left, 1 right, 2 up, 3 down)
float gFl = 1.0;                                                      // flicker: letters blink out on the beat
vec2 textUV(vec2 uv, float t, vec4 a, int anim, float react){
  float sc = max(0.05, uQ.x);
  int ad = int(uX.w + 0.5); bool vert = ad >= 2; float sg = (ad == 0 || ad == 3) ? 1.0 : -1.0;
  uv -= uX.xy * 0.5;                                                    // move the words around the frame
  if (anim == 1) sc *= 1.0 + a.w * 0.14 * react;                       // grows on every beat
  if (anim == 7) sc *= 1.0 + 0.10 * sin(t * 2.2) + a.x * 0.06 * react; // slow breathing zoom
  if (anim == 5) { float k = floor(uTime * 18.0);                       // shakes, harder on the kick
    uv += (vec2(hash(vec2(k, 1.3)), hash(vec2(2.1, k))) - 0.5) * (0.006 + a.w * 0.03 * react); }
  if (anim == 8) { float b = abs(sin(t * 3.0)) * (0.05 + a.w * 0.04 * react);   // bounces in the chosen direction
    uv += (vert ? vec2(0.0, b) : vec2(b, 0.0)) * -sg; }
  if (anim == 6) gFl = step(0.35 - a.w * 0.3 * react, hash(vec2(floor(uTime * 10.0 * max(0.2, uP.z)), 7.7)));
  vec2 q = (uv - 0.5) / sc + 0.5;
  int dr = int(uX.z + 0.5);
  if (dr >= 2) {                                                        // sideways: turn the words a quarter, keep them on screen
    vec2 rs = RES(); float as = rs.x / max(1.0, rs.y);
    vec2 c = (q - 0.5) * vec2(as, 1.0); c = dr == 2 ? vec2(c.y, -c.x) : vec2(-c.y, c.x); c *= as;
    q = c / vec2(as, 1.0) + 0.5;
  }
  if (anim == 2) { if (vert) q.x += sin(q.y * 9.0 + t * 3.0 * sg) * (0.012 + 0.025 * a.x * react);
                   else q.y += sin(q.x * 9.0 + t * 3.0 * sg) * (0.015 + 0.03 * a.x * react); }
  if (anim == 3) { if (vert) q.y = fract(q.y + t * 0.12 * sg); else q.x = fract(q.x + t * 0.12 * sg); }   // marquee
  if (anim == 4) {                                                      // tiled wall, rows (or columns) drift opposite ways
    vec2 g = vec2(2.0, 4.0) * max(0.5, uQ.y);
    vec2 c = uv * g;
    if (vert) { float col = floor(c.x); c.y += t * 0.15 * sg * (mod(col, 2.0) * 2.0 - 1.0) + col * 0.5; }
    else { float row = floor(c.y); c.x += t * 0.15 * sg * (mod(row, 2.0) * 2.0 - 1.0) + row * 0.5; }
    q = fract(c);
  }
  return q;
}
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  int mode = int(uP.x + 0.5), anim = int(uP.y + 0.5);
  float t = uTime * uP.z, react = uP.w;
  vec2 q = textUV(uv, t, a, anim, react);
  float front = 0.0;
  if (uM.z > 0.5) {                                                     // dissolve the old letters into the new ones
    float px1 = 1.0 / max(1.0, RES().y);
    // fine grain (letter-sized) + slow broad sweep: small words morph as smoothly as big ones
    float nz = 0.55 * fbm(uv * vec2(46.0, 26.0) + 2.7) + 0.45 * fbm(uv * vec2(3.0, 1.7) + 7.1);
    float k = uM.x * 1.5 - 0.25;
    gW = smoothstep(nz - 0.22, nz + 0.22, k);
    gW = mix(gW, uM.x, 0.25);                                           // a soft overall crossfade underneath
    vec2 fl = vec2(fbm(uv * 6.0 + 1.3), fbm(uv * 6.0 + 9.2)) - 0.5;
    gD = fl * px1 * 26.0;                                               // a few pixels of liquid drift
    front = smoothstep(0.0, 1.0, 1.0 - abs(gW * 2.0 - 1.0));
  }
  bool inside = q.x >= 0.0 && q.x <= 1.0 && q.y >= 0.0 && q.y <= 1.0;
  float m = inside ? T(q) * gFl : 0.0;
  vec2 px = PX() / max(0.05, uQ.x);
  // soft glow around the letters
  float gl = 0.0;
  for (int i = 0; i < 8; i++) { float an = float(i) * 0.785398; gl += T(q + vec2(cos(an), sin(an)) * px * 6.0) + T(q + vec2(cos(an), sin(an)) * px * 14.0) * 0.6; }
  gl = inside ? gl / 12.8 * gFl : 0.0;
  vec3 col = (uTA.w > 0.5 ? tTint(q) : uC.rgb) * (1.0 + a.w * 0.35 * react);
  vec3 sc = tex(uv), o = sc;
  if (mode == 0) o = mix(sc + col * gl * uC.w * 0.8, col, m);
  else if (mode == 1) o = sc * m * 1.5 + col * m * 0.10 + col * gl * uC.w * 0.35 * (1.0 - m);
  else if (mode == 2) o = sc * (1.0 - m) + col * m * 0.12 + col * gl * uC.w * 0.45 * (1.0 - m);
  else if (mode == 3) o = mix(sc, 1.0 - sc, m);
  else if (mode == 4) {
    float e = 0.0;
    for (int i = 0; i < 8; i++) { float an = float(i) * 0.785398; e += abs(m - T(q + vec2(cos(an), sin(an)) * px * (1.5 + 3.0 * uQ.z))); }
    e = clamp(e * 0.6, 0.0, 1.0);
    o = sc + col * (e * 1.6 + gl * uC.w * 0.25);
  }
  else if (mode == 5) {
    float row = floor(q.y * 24.0), tt = floor(uTime * 14.0);
    float j = step(0.75 - a.w * 0.4 * react, hash(vec2(row, tt))) * (hash(vec2(tt, row)) - 0.5) * 0.08;
    float s = 0.004 + a.w * 0.012 * react;
    vec3 tc = vec3(T(q + vec2(j + s, 0)), T(q + vec2(j, 0)), T(q + vec2(j - s, 0)));
    o = sc + tc * col * 1.2 + col * gl * uC.w * 0.3;
  }
  else if (mode == 6) {
    vec2 gr = vec2(T(q + vec2(px.x * 3.0, 0)) - T(q - vec2(px.x * 3.0, 0)), T(q + vec2(0, px.y * 3.0)) - T(q - vec2(0, px.y * 3.0)));
    o = tex(uv + gr * (0.03 + 0.04 * a.x * react)) * (1.0 + m * 0.25) + col * m * 0.08;
  }
  if (uM.z > 0.5) o += col * front * (m * 0.55 + gl * 0.35);           // soft glow where the letters change
  o = max(o, col * (m + gl * uC.w * 0.5) * uM.y);                      // during a dip the words stay lit on black
  fragColor = TDOutputSwizzle(vec4(mix(sc, clamp(o, 0.0, 1.5), uMix), 1.0));
}
