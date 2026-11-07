uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
uniform vec4 uQ;   // x drawing amount
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


// PHONE CAMERA SOURCE  input 0 = 3D render, input 1 = phone camera (any aspect, cover-fit)
// uP.x mode 1 cam only, 2 cam behind statue, 3 blend (screen), 4 statue seen through camera
// uP.y mirror (selfie cam)  uP.z feed alive 0..1 (fades out if the phone stops)  uMix amount
// uP.y = mirror (+1) + fit (+2): FILL crops the camera to the screen, FIT shows all of it with black bars
vec4 cam(vec2 uv){                       // .a = keyed alpha (green / blue screen removed); 1 elsewhere
  vec2 r0 = uTD2DInfos[0].res.zw, r1 = uTD2DInfos[1].res.zw;
  float a0 = r0.x / r0.y, a1 = r1.x / r1.y;
  bool mir = mod(uP.y, 2.0) > 0.5, fit = uP.y > 1.5;
  vec2 q = uv - 0.5;
  if (fit) { if (a1 > a0) q.y *= a1 / a0; else q.x *= a0 / a1; }
  else     { if (a1 > a0) q.x *= a0 / a1; else q.y *= a1 / a0; }
  if (mir) q.x = -q.x;
  vec2 p = q + 0.5;
  float inside = step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0);
  vec4 t = texture(sTD2DInputs[1], clamp(p, 0.0, 1.0));
  return vec4(t.rgb * clamp(uP.z, 0.0, 1.0) * inside, inside > 0.5 ? t.a : 1.0);
}
// uP.w statue amount (0 = statue switched off: effects run on the camera / clip only)
void main(){
  vec4 a = uAudio; vec2 uv = vUV.st;
  vec3 r = texture(sTD2DInputs[0], uv).rgb * clamp(uP.w, 0.0, 1.0);
  vec4 ck = cam(uv);
  vec3 c = ck.rgb * ck.a;                                    // keyed-out pixels are empty
  int m = int(floor(uP.x + 0.5));
  vec3 o;
  if (m == 0)      o = r;
  else if (m == 1) o = mix(r, ck.rgb, ck.a);                // the cut-out subject stands in front of the 3D scene
  else if (m == 2) { float k = smoothstep(0.07, 0.2, luma(r)); o = mix(c * (0.75 + a.x * 0.25), r, k); }
  else if (m == 3) o = 1.0 - (1.0 - r) * (1.0 - c * 0.85);
  else             o = r * smoothstep(0.08, 0.65, luma(c)) * 1.6 + c * 0.08;
  o = mix(r, o, uMix);
  // phone drawing on top (screen blend), same framing as the screen (the phone pad is 16:9)
  vec3 d = texture(sTD2DInputs[2], uv).rgb * uQ.x;
  o = 1.0 - (1.0 - o) * (1.0 - clamp(d, 0.0, 1.0));
  fragColor = TDOutputSwizzle(vec4(o, 1.0));
}
