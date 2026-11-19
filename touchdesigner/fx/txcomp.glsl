// text layers that have their own effects: laid back on top after the effects (text 1, then 2, then 3)
uniform vec4 uTS;   // effect chain (1-4, 0 none) of text 1, 2, 3
uniform vec4 uTL;   // blend mode of text 1, 2, 3 (0 normal, 1 add, 2 screen, 3 multiply, 4 overlay, 5 difference, 6 lighten, 7 darken)
uniform vec4 uTD;   // mask mode of text 1, 2, 3 (0 over, 1 mask, 2 cut-out, 3 invert)
layout(location = 0) out vec4 fragColor;
vec4 slotTex(int s, vec2 uv){ return s == 1 ? texture(sTD2DInputs[1], uv) : s == 2 ? texture(sTD2DInputs[2], uv) : s == 3 ? texture(sTD2DInputs[3], uv) : texture(sTD2DInputs[4], uv); }
vec3 put(vec3 o, vec4 L, int md, int bm){
  float a = clamp(L.a, 0.0, 1.0); vec3 c = clamp(L.rgb / max(L.a, 0.0001), 0.0, 4.0);
  if (md == 1) return o * a;
  if (md == 2) return o * (1.0 - a);
  if (md == 3) return mix(o, 1.0 - o, a);
  if (bm == 1) return o + L.rgb;
  if (bm == 2) return 1.0 - (1.0 - o) * (1.0 - clamp(L.rgb, 0.0, 1.0));
  if (bm == 3) return mix(o, o * c, a);
  if (bm == 4) return mix(o, mix(2.0 * o * c, 1.0 - 2.0 * (1.0 - o) * (1.0 - c), step(0.5, o)), a);
  if (bm == 5) return mix(o, abs(o - c), a);
  if (bm == 6) return mix(o, max(o, c), a);
  if (bm == 7) return mix(o, min(o, c), a);
  return o * (1.0 - a) + L.rgb;
}
void main(){
  vec2 uv = vUV.st; vec4 o = texture(sTD2DInputs[0], uv);
  float sl[3] = float[3](uTS.x, uTS.y, uTS.z), bl[3] = float[3](uTL.x, uTL.y, uTL.z), md[3] = float[3](uTD.x, uTD.y, uTD.z);
  for (int i = 0; i < 3; i++) { int s = int(floor(sl[i] + 0.5)); if (s > 0) o.rgb = put(o.rgb, slotTex(s, uv), int(md[i] + 0.5), int(bl[i] + 0.5)); }
  fragColor = TDOutputSwizzle(vec4(o.rgb, 1.0));
}
