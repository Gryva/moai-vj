// Projector output: 4-corner keystone (perspective warp), flips, soft edges, brightness, alignment test pattern.
// uH0..uH2 = rows of the inverse homography: projector pixel (0-1) -> picture (0-1), worked out by the engine.
uniform vec4 uH0; uniform vec4 uH1; uniform vec4 uH2;
uniform vec4 uK;   // x flip horizontal, y flip vertical, z edge softness, w test pattern (0 off, 1 grid over picture, 2 grid only)
uniform vec4 uB;   // x brightness, y black level lift, z gamma
layout(location = 0) out vec4 fragColor;

float grid(vec2 uv, vec2 res){
  vec2 px = 1.0 / res;
  vec2 g = abs(fract(uv * vec2(16.0, 9.0) + 0.5) - 0.5) / (vec2(16.0, 9.0) * px);   // distance to the grid in pixels
  float l = 1.0 - smoothstep(0.6, 1.6, min(g.x, g.y));
  vec2 c = abs(uv - 0.5) / px;                                                       // centre cross
  l = max(l, 1.0 - smoothstep(1.0, 2.5, min(c.x, c.y)));
  vec2 e = min(uv, 1.0 - uv) / px;                                                   // thick border
  l = max(l, 1.0 - smoothstep(4.0, 6.0, min(e.x, e.y)));
  vec2 q = (uv - 0.5) * vec2(res.x / res.y, 1.0);                                    // circle: stays round when the shape is right
  l = max(l, 1.0 - smoothstep(1.0, 2.5, abs(length(q) - 0.42) * res.y));
  return l;
}

void main(){
  vec2 p = vUV.st;
  vec3 h = vec3(dot(uH0.xyz, vec3(p, 1.0)), dot(uH1.xyz, vec3(p, 1.0)), dot(uH2.xyz, vec3(p, 1.0)));
  if (abs(h.z) < 1e-6) { fragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec2 uv = h.xy / h.z;
  if (h.z < 0.0 || any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) { fragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
  vec2 s = uv;
  if (uK.x > 0.5) s.x = 1.0 - s.x;
  if (uK.y > 0.5) s.y = 1.0 - s.y;
  vec3 c = texture(sTD2DInputs[0], s).rgb;
  c = pow(max(c, 0.0), vec3(1.0 / max(0.2, uB.z))) * uB.x + uB.y;
  int t = int(uK.w + 0.5);
  if (t > 0) {
    vec2 res = uTD2DInfos[0].res.zw;
    float g = grid(uv, res);
    if (t == 2) c = vec3(0.04);
    c = mix(c, vec3(1.0), g);
    vec2 cn = min(uv, 1.0 - uv);                                                     // corner markers: TL red, TR green, BL blue, BR yellow
    if (cn.x < 0.06 && cn.y < 0.06 * res.x / res.y) {
      vec3 m = uv.y > 0.5 ? (uv.x < 0.5 ? vec3(1.0, 0.2, 0.2) : vec3(0.2, 1.0, 0.3)) : (uv.x < 0.5 ? vec3(0.3, 0.5, 1.0) : vec3(1.0, 0.9, 0.2));
      c = mix(c, m, 0.85);
    }
  }
  float f = max(0.0, uK.z);                                                          // soft edges
  if (f > 0.0) { vec2 e = min(uv, 1.0 - uv); c *= smoothstep(0.0, f, e.x) * smoothstep(0.0, f, e.y); }
  fragColor = TDOutputSwizzle(vec4(clamp(c, 0.0, 1.0), 1.0));
}
