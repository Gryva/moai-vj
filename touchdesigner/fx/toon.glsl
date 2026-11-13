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
#define OUT(c) fragColor = TDOutputSwizzle(outc(vUV.st, (c)))
// TOON  cartoon look: flat vibrant colour bands + a thick outline around shapes and inner lines.
// uP.x = outline thickness (0-1). Outline colour: OWN = white, or any colour / gradient from the Colour box. Inner lines are dark.
vec3 cel(vec3 c){
  float l = luma(c);
  float b = (floor(l * 4.0) + smoothstep(0.35, 0.65, fract(l * 4.0))) / 4.0;     // 4 soft-edged light bands
  vec3 h = c / max(1e-3, max(c.r, max(c.g, c.b)));                               // pure hue of the pixel
  vec3 v = mix(vec3(luma(h)), h, 1.55);                                          // pushed saturation: vibrant
  return clamp(v * (0.12 + b * 1.05), 0.0, 1.0);
}
bool SOLID = false;                                                              // whole picture: black background = empty
float shp(vec4 t){ return SOLID ? smoothstep(0.03, 0.09, max(t.r, max(t.g, t.b))) : t.a; }
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; vec2 px = PX();
  SOLID = texture(sTD2DInputs[0], vec2(0.02)).a * texture(sTD2DInputs[0], vec2(0.98)).a * texture(sTD2DInputs[0], vec2(0.02, 0.98)).a * texture(sTD2DInputs[0], vec2(0.98, 0.02)).a > 0.99;
  float th = 1.0 + clamp(uP.x, 0.0, 1.0) * 11.0 * (1.0 + a.w * 0.25);            // outline width in pixels (kicks fatten it)
  vec4 s0 = texture(sTD2DInputs[0], uv);
  vec3 sm = (tex(uv) * 2.0 + tex(uv + vec2(px.x, 0.0)) + tex(uv - vec2(px.x, 0.0)) + tex(uv + vec2(0.0, px.y)) + tex(uv - vec2(0.0, px.y))) / 6.0;
  vec3 c = cel(sm);
  float L0 = luma(cel(sm));
  float sil = 0.0, inner = 0.0;
  for (int k = 0; k < 16; k++) {                                                 // look around in a ring: the outer shape + strong colour changes
    float an = float(k) * 0.3927;
    vec2 d = vec2(cos(an), sin(an)) * px;
    vec4 t1 = texture(sTD2DInputs[0], uv + d * th);
    vec4 t2 = texture(sTD2DInputs[0], uv + d * th * 0.5);
    sil = max(sil, max(shp(t1), shp(t2)));
    inner = max(inner, abs(luma(cel(t2.rgb)) - L0));
  }
  float s0a = shp(s0);
  float outer = sil * (1.0 - smoothstep(0.3, 0.6, s0a));                        // just outside a cut-out shape
  float inl = smoothstep(0.22, 0.36, inner) * step(0.3, s0a) * (1.0 - outer);  // dark lines inside where the colour jumps
  vec3 ink = fxTint(vec3(0.97), uv);                                             // the border: white unless you pick a colour
  c = mix(c, vec3(0.03), inl);
  c = mix(c, ink, outer);
  gA = max(gA, outer); gA1 = max(gA1, outer);                                     // the outline itself is visible, also around see-through shapes
  OUT(c);
}
