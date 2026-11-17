// RECTANGLE LAYER  output = straight RGBA (the card itself, transparent around it)
// uA = (colour A, fill 0 solid / 1 linear / 2 radial / 3 conic / 4 stripes / 5 glass)
// uB = (colour B, angle in radians)
// uS = (width 0..1, height 0..1, corner roundness 0..1, outline 0 = filled .. 1 = thick line)
// uE = (soft edge 0..1, flow speed, beat glow 0..1, stripes count)
// uT = (time, beat pulse 0..1)
uniform vec4 uA;
uniform vec4 uB;
uniform vec4 uS;
uniform vec4 uE;
uniform vec4 uT;
out vec4 fragColor;

float box(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }

void main(){
  vec2 res = uTDOutputInfo.res.zw; float as = res.x / res.y;
  vec2 p = (vUV.st - 0.5) * vec2(as, 1.0);
  vec2 hb = max(vec2(uS.x * as, uS.y) * 0.5, vec2(0.002));
  float r = clamp(uS.z, 0.0, 1.0) * min(hb.x, hb.y);
  float d = box(p, hb, r);
  float aa = max(fwidth(d), 1e-4), sf = uE.x * 0.25 * min(hb.x, hb.y) + aa;
  float fill = 1.0 - smoothstep(-sf, aa, d);                                  // soft edge fades inward
  if (uS.w > 0.001) { float lw = uS.w * 0.5 * min(hb.x, hb.y); fill *= smoothstep(-lw - aa - sf * 0.5, -lw + aa, d); }   // outline only

  vec2 q = p / (hb * 2.0);                                                    // -0.5..0.5 across the card
  vec2 dir = vec2(cos(uB.w), sin(uB.w));
  float fl = uT.x * uE.y * 0.25, t = 0.0;
  int m = int(uA.w + 0.5);
  if (m == 1) t = dot(q, dir) + 0.5;
  else if (m == 2) t = length(q * 2.0) / 1.4142;                           // centre -> corners
  else if (m == 3) t = atan(q.y, q.x) / 6.2831853 + 0.5 - uB.w / 6.2831853;
  else if (m == 4) t = dot(q * vec2(hb.x / max(hb.y, 1e-3), 1.0), dir) * max(1.0, uE.w);
  else if (m == 5) t = 1.0 - (q.y + 0.5);
  if (m == 1 || m == 2) t = uE.y > 0.001 ? 0.5 - 0.5 * cos((t - fl) * 6.2831853) : clamp(t, 0.0, 1.0);   // flowing gradients loop smoothly
  if (m == 3) t = 1.0 - abs(2.0 * fract(t - fl) - 1.0);                       // no seam: A -> B -> A around the centre
  if (m == 4) { float s = fract(t - fl); float w = fwidth(t) * 1.5; t = smoothstep(0.5 - w, 0.5 + w, s) * (1.0 - smoothstep(1.0 - w, 1.0, s)); }
  vec3 col = m == 0 ? uA.rgb : mix(uA.rgb, uB.rgb, clamp(t, 0.0, 1.0));
  if (m == 5) {                                                               // GLASS: a soft sheen band and a bright rim
    float band = smoothstep(0.18, 0.0, abs(dot(q, vec2(0.7071, 0.7071)) - fract(fl + 0.4) * 2.0 + 1.0));
    float rim = smoothstep(-0.035 * min(hb.x, hb.y) * 6.0, 0.0, d);
    col = mix(uA.rgb, uB.rgb, clamp(t, 0.0, 1.0)) + band * 0.35 + rim * 0.45;
    fill *= mix(0.55, 1.0, rim);
  }
  col *= 1.0 + uE.z * uT.y * 0.9;                                             // beat: the card flashes brighter on the kick
  fragColor = TDOutputSwizzle(vec4(col, clamp(fill, 0.0, 1.0)));
}
