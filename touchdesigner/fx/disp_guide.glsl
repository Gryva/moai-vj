// SCREEN-ONLY overlay for the projector window (OUT, the stream and the recording never see it)
// uG = (9:16 frame on, recording, frame left, frame right)   uT.x = time
uniform vec4 uG;
uniform vec4 uT;
layout(location = 0) out vec4 fragColor;
int glyph(int k){ return k == 0 ? 0x6BAD : k == 1 ? 0x79A7 : 0x3923; }   // R E C, 3x5, top row first
float txt(vec2 q){                                                 // "REC" at 3 px per dot, q = pixels from its top-left
  ivec2 c = ivec2(floor(q / 3.0)); if (c.y < 0 || c.y > 4 || c.x < 0 || c.x > 10) return 0.0;
  int k = c.x / 4, x = c.x - k * 4; if (x > 2) return 0.0;
  int bit = 14 - (c.y * 3 + x); return float((glyph(k) >> bit) & 1); }
void main(){
  vec4 c = texture(sTD2DInputs[0], vUV.st);
  vec2 res = uTD2DInfos[0].res.zw, p = vUV.st * res;
  float rec = uG.y, L = uG.x > 0.5 ? uG.z * res.x : 0.0, R = uG.x > 0.5 ? uG.w * res.x : res.x;
  vec3 col = rec > 0.5 ? vec3(1.0, 0.16, 0.16) : vec3(0.78, 1.0, 0.24);
  float stripe = step(0.5, fract((p.x + p.y) / 16.0 - uT.x * 0.6));
  if (uG.x > 0.5) {
    if (p.x < L || p.x > R) c.rgb *= 0.4;
    float bw = 6.0, inb = (p.x >= L && p.x <= R) ? 1.0 : 0.0;
    float edge = inb * max(max(step(p.x, L + bw), step(R - bw, p.x)), max(step(p.y, bw), step(res.y - bw, p.y)));
    if (edge > 0.5) c.rgb = mix(vec3(0.0), col, stripe);
  }
  if (rec > 0.5 && uG.x < 0.5) {                                  // 16:9 take: red stripes round the whole screen
    float bw = 6.0, edge = max(max(step(p.x, bw), step(res.x - bw, p.x)), max(step(p.y, bw), step(res.y - bw, p.y)));
    if (edge > 0.5) c.rgb = mix(vec3(0.0), col, stripe);
  }
  if (rec > 0.5) {
    vec2 o = vec2(L + 26.0, res.y - 26.0);
    float blink = 0.55 + 0.45 * step(0.0, sin(uT.x * 6.2832));
    float dot_ = 1.0 - smoothstep(7.0, 9.0, length(p - o));
    c.rgb = mix(c.rgb, vec3(1.0, 0.12, 0.12), dot_ * blink);
    float t = txt(vec2(p.x - (o.x + 16.0), (res.y - p.y) - (res.y - o.y - 7.0)));
    vec2 sh = vec2(p.x - (o.x + 17.0), (res.y - p.y) - (res.y - o.y - 8.0));
    c.rgb = mix(c.rgb, vec3(0.0), txt(sh) * 0.8 * (1.0 - t));
    c.rgb = mix(c.rgb, vec3(1.0), t);
  }
  fragColor = TDOutputSwizzle(c);
}
