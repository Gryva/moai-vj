uniform float uTime;
uniform vec4 uAudio;
uniform float uMix;
uniform vec4 uP;
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

void main(){
  vec4 a = uAudio; vec2 uv = vUV.st; float t = uTime;
  vec2 w = vec2(fbm(uv * 3.0 + t * 0.25), fbm(uv * 3.0 + 5.2 - t * 0.2)) - 0.5;
  uv += w * (0.04 + a.x * 0.18);
  vec3 c = tex(uv); float l = luma(c);
  c = mix(c, vec3(l) * vec3(1.1, 0.95, 0.8), 0.5);
  float levels = 6.0 - floor(a.y * 3.0);
  c = floor(c * levels) / levels;
  c += (hash(floor(vUV.st * RES() / 2.0) + fract(t) * 91.0) - 0.5) * (0.2 + a.z * 0.35);
  c *= 1.0 - 0.8 * pow(length(vUV.st - 0.5), 2.0);
  c += a.w * 0.08;
  fragColor = TDOutputSwizzle(vec4(mix(tex(vUV.st), c, uMix), 1.0));
}