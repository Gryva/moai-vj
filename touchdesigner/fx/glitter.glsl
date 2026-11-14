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
vec2 PX(){ return uTD2DInfos[0].res.xy; }
vec2 RES(){ return uTD2DInfos[0].res.zw; }

vec3 rgb2hsv(vec3 c){ vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0); vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g)); vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r)); float d = q.x - min(q.w, q.y); float e = 1.0e-10; return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x); }
float ASP(){ vec2 r = RES(); return r.x / r.y; }
#define OUT(c) fragColor = TDOutputSwizzle(outc(vUV.st, (c)))

// GLITTER CORE  sparkly 2000s glitter-text look for text, logos, anything with a shape. Original take, drawn here, no images.
// uP.x = beat * 1000000 + style * 10000 + glitter amount * 100 + sparkle speed   (amount, speed 0-99; beat 0 steady / 1 sparkles flash with the kick)
// styles: 0 pink  1 baby blue  2 purple  3 gold  4 disco silver  5 rainbow  6 hearts  7 starry night  8 jelly candy  9 blush
float h21(vec2 p){ p = fract(p * vec2(233.34, 851.73)); p += dot(p, p + 23.45); return fract(p.x * p.y); }
vec3 hsvG(float h, float s, float v){ vec3 k = clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1.0), k, s); }
float A(vec2 uv){ return texture(sTD2DInputs[0], uv).a; }
float heart(vec2 p){ p.y -= 0.25; p.x = abs(p.x); float a = atan(p.x, p.y) / 3.14159, r = length(p); float h = abs(a); float d = (13.0 * h - 22.0 * h * h + 10.0 * h * h * h) / (6.0 - 5.0 * h); return smoothstep(d * 0.5 + 0.04, d * 0.5 - 0.04, r); }
float star(vec2 p){ p = abs(p); return clamp(max(0.0, 1.0 - 30.0 * p.x * p.y - 1.6 * (p.x + p.y)) * 1.5 + exp(-dot(p, p) * 60.0), 0.0, 1.5); }
void main(){
  vec2 uv = vUV.st; vec4 a4 = uAudio; vec2 px = PX();
  float q = uP.x, beat = floor(q / 1000000.0 + 0.001); q -= beat * 1000000.0;
  float sty = floor(q / 10000.0 + 0.001); q -= sty * 10000.0; float amt = floor(q / 100.0 + 0.001) / 99.0, spd = (q - floor(q / 100.0 + 0.001) * 100.0) / 99.0;
  vec4 src = texture(sTD2DInputs[0], uv); float a = src.a;
  // outline + glow from the letter shape
  float o1 = 0.0, o2 = 0.0;
  for (int k = 0; k < 12; k++) { float an = float(k) * 0.5236; vec2 d = vec2(cos(an), sin(an));
    o1 = max(o1, A(uv + d * px * 2.5)); o2 += A(uv + d * px * 9.0) + A(uv + d * px * 5.0); }
  o2 /= 24.0; float rim = clamp(o1 - a, 0.0, 1.0);
  // palette
  vec3 c1, c2, ol = vec3(1.0), gl;
  if (sty < 0.5) { c1 = vec3(1.0, 0.25, 0.7); c2 = vec3(1.0, 0.75, 0.92); }
  else if (sty < 1.5) { c1 = vec3(0.3, 0.7, 1.0); c2 = vec3(0.8, 0.95, 1.0); }
  else if (sty < 2.5) { c1 = vec3(0.55, 0.2, 1.0); c2 = vec3(0.9, 0.7, 1.0); }
  else if (sty < 3.5) { c1 = vec3(0.85, 0.55, 0.08); c2 = vec3(1.0, 0.92, 0.55); ol = vec3(1.0, 0.97, 0.8); }
  else if (sty < 4.5) { c1 = vec3(0.45); c2 = vec3(1.0); }
  else if (sty < 5.5) { c1 = hsvG(fract(uv.x * 1.5 - uTime * (0.05 + spd * 0.3)), 0.75, 1.0); c2 = hsvG(fract(uv.x * 1.5 + 0.15 - uTime * (0.05 + spd * 0.3)), 0.35, 1.0); }
  else if (sty < 6.5) { c1 = vec3(0.95, 0.08, 0.3); c2 = vec3(1.0, 0.55, 0.7); }
  else if (sty < 7.5) { c1 = vec3(0.05, 0.08, 0.35); c2 = vec3(0.35, 0.5, 1.0); ol = vec3(0.7, 0.85, 1.0); }
  else if (sty < 8.5) { c1 = vec3(0.1, 0.85, 0.75); c2 = vec3(0.7, 1.0, 0.95); ol = vec3(0.02, 0.25, 0.2); }
  else { c1 = vec3(0.95, 0.55, 0.62); c2 = vec3(1.0, 0.88, 0.85); }
  gl = mix(c1, c2, 0.4);
  // glitter grain: tiny cells that twinkle at their own pace
  float cell = sty > 3.5 && sty < 4.5 ? 5.0 : 2.0;
  vec2 g = floor(uv / (px * cell)); float r = h21(g), r2 = h21(g + 17.0);
  float sp = 0.6 + spd * 7.0, kick = beat > 0.5 ? a4.w * 1.5 + a4.x * 0.5 : 0.0;
  float tw = pow(0.5 + 0.5 * sin(uTime * sp * (0.6 + r2) + r * 6.2832), 6.0) * (1.0 + kick);
  vec3 fill = mix(c1, c2, r) * (0.55 + 0.45 * r2);
  fill += vec3(1.0) * tw * (0.25 + amt * 1.1);
  if (sty > 7.5 && sty < 8.5) {                                        // jelly: glossy candy, no grains
    float top = smoothstep(0.0, 1.0, (A(uv - vec2(0.0, px.y * 6.0)) - A(uv + vec2(0.0, px.y * 6.0))) * 0.5 + 0.5);
    fill = mix(c1, c2, top) + vec3(1.0) * smoothstep(0.55, 0.9, A(uv - vec2(0.0, px.y * 8.0)) * (1.0 - A(uv + vec2(0.0, px.y * 3.0)) * 0.6)) * 0.6; }
  fill = mix(gl * 0.8, fill, 0.35 + amt * 0.65);
  // sparkles: stars (or hearts) that pop on the letters
  vec2 asp = vec2(1.0, px.y / px.x); float grid = 0.05;
  vec2 sc = uv / asp / grid, id = floor(sc), f = fract(sc) - 0.5;
  float sr = h21(id + 3.1), life = fract(uTime * (0.15 + spd * 0.6) + sr);
  vec2 ctr = (id + 0.5 + (vec2(h21(id + 7.7), h21(id + 9.3)) - 0.5) * 0.6) * grid * asp;
  float onL = max(max(A(ctr), A(ctr + vec2(px.x * 8.0, 0.0))), max(A(ctr - vec2(px.x * 8.0, 0.0)), max(A(ctr + vec2(0.0, px.y * 8.0)), A(ctr - vec2(0.0, px.y * 8.0))))), pop = smoothstep(0.0, 0.15, life) * smoothstep(0.6, 0.2, life) * step(0.55 - amt * 0.35 - kick * 0.2, sr);
  vec2 sp2 = (f - (vec2(h21(id + 7.7), h21(id + 9.3)) - 0.5) * 0.6) / (0.45 + 0.3 * sr);
  float spark = (sty > 5.5 && sty < 6.5 ? heart(sp2 * 0.9) : star(sp2)) * pop * onL;
  vec3 sparkC = sty > 5.5 && sty < 6.5 ? vec3(1.0, 0.3, 0.55) : vec3(1.0);
  // put it together: glow, outline, glitter fill, sparkles
  vec3 col = gl * 1.3;
  float al = clamp(o2 * 1.1, 0.0, 1.0) * (0.55 + 0.25 * amt);
  col = mix(col, ol, rim); al = max(al, rim);
  col = mix(col, fill, a); al = max(al, a);
  col += sparkC * spark * 1.4; al = max(al, clamp(spark, 0.0, 1.0));
  vec4 o = vec4(col * al, al);
  fragColor = TDOutputSwizzle(mix(src, o, uMix));
}
