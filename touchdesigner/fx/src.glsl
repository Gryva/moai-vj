uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
uniform vec4 uQ;   // x drawing amount
uniform vec4 uO;   // layer order, back to front: ids 1 3D models, 2 phone camera, 3 images, 4 videos, 5 drawing (0 = empty)
uniform vec4 uO2;  // order slots 5..8
uniform vec4 uA;   // amounts: x 3D models, y camera, z images, w videos
layout(location = 0) out vec4 fragColor;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int i=0;i<5;i++){ v += a*vnoise(p); p *= 2.03; a *= 0.5; } return v; }
vec3 tex(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)).rgb; }
float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 hsv(float h, float s, float v){ vec3 k = clamp(abs(mod(h*6.0 + vec3(0,4,2), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1.0), k, s); }
vec2 PX(){ return uTD2DInfos[0].res.xy; }
vec2 RES(){ return uTD2DInfos[0].res.zw; }


// LAYERED SOURCE  inputs: 0 3D render (premultiplied), 1 phone camera / clip, 2 drawing, 3 images (keyed, straight alpha), 4 videos
// uP.x camera blend: 1/2 normal, 3 blend (screen), 4 mask   uP.y mirror (+1, camera only) + whole image (+2)
vec4 fitTex(int i, vec2 uv, bool mir){       // .rgb colour, .a = alpha (keyed alpha x inside the picture)
  vec2 r0 = uTD2DInfos[0].res.zw, r1 = uTD2DInfos[i].res.zw;
  float a0 = r0.x / r0.y, a1 = r1.x / r1.y;
  bool fit = uP.y > 1.5;
  vec2 q = uv - 0.5;
  if (fit) { if (a1 > a0) q.y *= a1 / a0; else q.x *= a0 / a1; }
  else     { if (a1 > a0) q.x *= a0 / a1; else q.y *= a1 / a0; }
  if (mir) q.x = -q.x;
  vec2 p = q + 0.5;
  float inside = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0);
  vec4 t = i == 1 ? texture(sTD2DInputs[1], clamp(p, 0.0, 1.0)) : i == 3 ? texture(sTD2DInputs[3], clamp(p, 0.0, 1.0)) : texture(sTD2DInputs[4], clamp(p, 0.0, 1.0));
  return vec4(t.rgb, (i == 1 ? 1.0 : t.a) * inside);
}
vec3 layer(int id, vec2 uv, vec3 o){
  if (id == 1) { vec4 r = texture(sTD2DInputs[0], uv); float w = clamp(uA.x, 0.0, 1.0); return o * (1.0 - clamp(r.a, 0.0, 1.0) * w) + r.rgb * w; }
  if (id == 2) {
    if (uA.y < 0.002) return o;
    vec4 c = fitTex(1, uv, mod(uP.y, 2.0) > 0.5); float k = clamp(uA.y, 0.0, 1.0);
    int m = int(floor(uP.x + 0.5));
    if (m == 3) return 1.0 - (1.0 - o) * (1.0 - c.rgb * c.a * 0.85 * k);
    if (m == 4) return mix(o, o * smoothstep(0.08, 0.65, luma(c.rgb)) * 1.6 + c.rgb * 0.08, k * c.a);
    return mix(o, c.rgb, c.a * k);
  }
  if (id == 3 || id == 4) {
    float k = clamp(id == 3 ? uA.z : uA.w, 0.0, 1.0); if (k < 0.002) return o;
    vec4 c = fitTex(id, uv, false); return mix(o, c.rgb, c.a * k);
  }
  if (id == 5) { vec3 d = clamp(texture(sTD2DInputs[2], uv).rgb * uQ.x, 0.0, 1.0); return 1.0 - (1.0 - o) * (1.0 - d); }
  return o;
}
void main(){
  vec2 uv = vUV.st; vec3 o = vec3(0.0);
  float ids[8] = float[8](uO.x, uO.y, uO.z, uO.w, uO2.x, uO2.y, uO2.z, uO2.w);
  for (int i = 0; i < 8; i++) o = layer(int(ids[i] + 0.5), uv, o);
  fragColor = TDOutputSwizzle(vec4(o, 1.0));
}
