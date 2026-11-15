// PRESET TRANSITIONS  input 0 = the new look (live), input 1 = the old look (frozen when the change started)
// uTR = (mode 1 crossfade / 2 wipe / 3 zoom / 4 glitch / 5 clock / 6 iris / 7 doors / 8 curtain bars / 9 diamond / 10 lucas wipe, progress 0..1, seed, 0)
uniform vec4 uTR;
layout(location = 0) out vec4 fragColor;
float h1(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec4 A(vec2 uv){ return texture(sTD2DInputs[0], clamp(uv, 0.0, 1.0)); }
vec4 B(vec2 uv){ return texture(sTD2DInputs[1], clamp(uv, 0.0, 1.0)); }
void main(){
  vec2 uv = vUV.st; int m = int(uTR.x + 0.5); float u = clamp(uTR.y, 0.0, 1.0), e = u * u * (3.0 - 2.0 * u);
  vec4 c; vec2 res = uTDOutputInfo.res.zw; float asp = res.x / max(res.y, 1.0); vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  if (m == 5) {                                   // CLOCK: a hand sweeps round from 12 o'clock
    float a = fract(atan(p.x, p.y) / 6.2831853 + 1.0);  // 0..1 clockwise from 12 o'clock
    c = mix(B(uv), A(uv), smoothstep(a - 0.01, a + 0.01, e * 1.02));
  } else if (m == 6) {                            // IRIS: a circle opens from the middle
    float r = length(p) / length(vec2(asp, 1.0) * 0.5);
    c = mix(B(uv), A(uv), 1.0 - smoothstep(e * 1.04 - 0.02, e * 1.04, r));
  } else if (m == 7) {                            // DOORS: opens from the middle out to both sides
    float d = abs(uv.x - 0.5) * 2.0;
    c = mix(B(uv), A(uv), 1.0 - smoothstep(e * 1.03 - 0.015, e * 1.03, d));
  } else if (m == 8) {                            // CURTAIN: black bars lead the opening from the middle out
    float d = abs(uv.y - 0.5) * 2.0, edge = e * 1.25;
    c = d < edge - 0.25 ? A(uv) : (d < edge ? vec4(0.0, 0.0, 0.0, 1.0) : B(uv));
  } else if (m == 9) {                            // DIAMOND: a diamond opens from the middle
    float r = (abs(p.x) + abs(p.y)) / (asp * 0.5 + 0.5);
    c = mix(B(uv), A(uv), 1.0 - smoothstep(e * 1.04 - 0.02, e * 1.04, r));
  } else if (m == 10) {                           // LUCAS: the classic hard-edged sideways wipe
    c = uv.x < e * 1.002 ? A(uv) : B(uv);
  } else if (m == 2) {                                   // WIPE: a soft bright edge sweeps left to right
    float x = e * 1.12 - 0.06, d = uv.x - x;
    c = mix(A(uv), B(uv), smoothstep(-0.02, 0.02, d));
    c.rgb += vec3(0.9, 1.0, 0.6) * exp(-abs(d) * 160.0) * (1.0 - abs(2.0 * u - 1.0)) * 0.8;
  } else if (m == 3) {                            // ZOOM: the old look rushes past the camera, the new one settles in
    vec2 o = (uv - 0.5) / (1.0 + e * 2.5) + 0.5, n = (uv - 0.5) * (1.12 - 0.12 * e) + 0.5;
    c = mix(B(o), A(n), smoothstep(0.15, 0.85, u));
  } else if (m == 4) {                            // GLITCH: blocks jump between the two looks, with colour tearing
    vec2 bl = floor(uv * vec2(18.0, 12.0)); float t = floor(u * 14.0);
    float r = h1(bl + t + uTR.z * 31.0); float shift = (h1(vec2(bl.y, t)) - 0.5) * 0.08 * (1.0 - abs(2.0 * u - 1.0));
    vec2 q = vec2(uv.x + shift, uv.y);
    vec4 a = vec4(A(q + vec2(0.006, 0.0)).r, A(q).g, A(q - vec2(0.006, 0.0)).b, A(q).a);
    vec4 b = vec4(B(q - vec2(0.006, 0.0)).r, B(q).g, B(q + vec2(0.006, 0.0)).b, B(q).a);
    c = r < e ? a : b;
  } else {                                        // CROSSFADE
    c = mix(B(uv), A(uv), e);
  }
  fragColor = TDOutputSwizzle(c);
}
