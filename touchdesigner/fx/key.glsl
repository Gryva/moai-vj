// BACKGROUND KEYER  input 0 = image or video, output = straight RGBA (subject kept, background colour made transparent)
// uK = (on, colour 0 auto / 1 green / 2 blue / 3 picked colour, tolerance, softness)   uKC = picked colour (rgb)   uS = (spill removal, shrink edges px, 0, 0)
uniform vec4 uK;
uniform vec4 uS;
uniform vec4 uKC;
uniform vec4 uC;   // crop: x left, y right, z top, w bottom (0..0.45)
layout(location = 0) out vec4 fragColor;
vec2 cc(vec3 c){ return vec2(-0.169 * c.r - 0.331 * c.g + 0.5 * c.b, 0.5 * c.r - 0.419 * c.g - 0.081 * c.b); }
vec2 crop(vec2 uv){ return vec2(uC.x + uv.x * (1.0 - uC.x - uC.y), uC.w + uv.y * (1.0 - uC.z - uC.w)); }
vec3 src(vec2 uv){ return texture(sTD2DInputs[0], clamp(crop(uv), 0.0, 1.0)).rgb; }
vec3 KEY;
void pickKey(){
  // sample the frame border: the screen is whatever surrounds the subject
  int mode = int(uK.y + 0.5);
  if (mode == 3) { KEY = uKC.rgb; return; }                     // a colour picked on the remote: any colour, also black or white
  vec3 acc = vec3(0.0); float n = 0.0;
  for (int i = 0; i < 20; i++) {
    float t = (float(i) + 0.5) / 20.0;
    vec3 s[4] = vec3[4](src(vec2(t, 0.03)), src(vec2(t, 0.97)), src(vec2(0.03, t)), src(vec2(0.97, t)));
    for (int j = 0; j < 4; j++) {
      vec3 c = s[j];
      bool ok = mode == 1 ? (c.g > c.r * 1.08 && c.g > c.b * 1.08) : mode == 2 ? (c.b > c.r * 1.08 && c.b > c.g * 1.02) : (max(c.r, max(c.g, c.b)) - min(c.r, min(c.g, c.b)) > 0.12);
      if (ok) { acc += c; n += 1.0; }
    }
  }
  vec3 def = mode == 2 ? vec3(0.1, 0.25, 0.85) : vec3(0.15, 0.75, 0.2);
  KEY = n > 3.0 ? acc / n : def;
}
float alphaAt(vec2 uv){
  vec3 c = src(uv);
  float d = length(cc(c) - cc(KEY)) * 2.4;                  // chroma distance from the screen colour
  float ks = max(KEY.r, max(KEY.g, KEY.b)) - min(KEY.r, min(KEY.g, KEY.b));
  if (int(uK.y + 0.5) == 3) {                               // greys / black / white have no hue: brightness has to count too
    float lw = mix(1.6, 0.35, smoothstep(0.08, 0.35, ks));
    d = length(vec3(cc(c) - cc(KEY), (dot(c, vec3(0.299, 0.587, 0.114)) - dot(KEY, vec3(0.299, 0.587, 0.114))) * lw)) * 2.4;
  }
  float tol = uK.z * 0.6, soft = 0.02 + uK.w * 0.5;
  return smoothstep(tol, tol + soft, d);
}
void main(){
  vec2 uv = vUV.st;
  vec3 c = src(uv);
  if (uK.x < 0.5) { fragColor = TDOutputSwizzle(vec4(c, texture(sTD2DInputs[0], clamp(crop(vUV.st), 0.0, 1.0)).a)); return; }   // no key: keep the file's own see-through parts
  pickKey();
  float a = alphaAt(uv);
  if (uS.y > 0.01) {                                         // choke: pull the edge in by a few pixels
    vec2 px = uTD2DInfos[0].res.xy * uS.y;
    a = min(a, min(min(alphaAt(uv + vec2(px.x, 0)), alphaAt(uv - vec2(px.x, 0))), min(alphaAt(uv + vec2(0, px.y)), alphaAt(uv - vec2(0, px.y)))));
  }
  vec2 e = min(uv, 1.0 - uv);                                 // the outermost pixels of a video are often junk
  a *= smoothstep(0.002, 0.006, min(e.x, e.y));
  // spill: remove the screen colour that bounced onto the subject's edges
  float l = dot(c, vec3(0.299, 0.587, 0.114));
  vec3 kd = KEY - vec3(dot(KEY, vec3(0.299, 0.587, 0.114)));
  float kl = max(1e-3, length(kd)); kd /= kl;
  float sp = max(0.0, dot(c - vec3(l), kd));
  float kss = max(KEY.r, max(KEY.g, KEY.b)) - min(KEY.r, min(KEY.g, KEY.b));
  c -= kd * sp * uS.x * smoothstep(0.08, 0.3, kss);       // no spill fix for grey / black / white backgrounds
  c = max(c, 0.0);
  fragColor = TDOutputSwizzle(vec4(c, a));
}
