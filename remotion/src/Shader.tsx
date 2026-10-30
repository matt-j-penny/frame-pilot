import { ThreeCanvas } from "@remotion/three";
import { useMemo } from "react";
import * as THREE from "three";
import { useCurrentFrame, useVideoConfig } from "remotion";

// WebGL backgrounds: fragment-shader presets (aurora, silk) and a three.js scene (glass).
// Everything is driven by the frame number, so renders are deterministic.

const VERT = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const NOISE = `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.02; a *= 0.5; } return v; }
`;

const FRAG: Record<string, string> = {
  // soft drifting colour fields with fine light streaks
  aurora: `
uniform float uTime, uGrain; uniform vec3 uA, uB, uC, uBase; varying vec2 vUv;
${NOISE}
void main() {
  vec2 p = vUv * vec2(1.0, 1.78);
  float t = uTime * 0.12;
  float n1 = fbm(p * 1.6 + vec2(t, -t * 0.7));
  float n2 = fbm(p * 2.3 - vec2(t * 0.6, t) + n1);
  vec3 col = uBase;
  col = mix(col, uA, smoothstep(0.35, 0.85, n1) * 0.55);
  col = mix(col, uB, smoothstep(0.45, 0.9, n2) * 0.45);
  float streak = smoothstep(0.015, 0.0, abs(fract(p.y * 9.0 + n2 * 2.0 - t) - 0.5) - 0.48);
  col = mix(col, uC, streak * 0.12);
  col += (hash(vUv * 1000.0 + uTime) - 0.5) * uGrain;
  gl_FragColor = vec4(col, 1.0);
}`,
  // flowing satin folds with a moving specular sheen
  silk: `
uniform float uTime, uGrain; uniform vec3 uA, uB, uC, uBase; varying vec2 vUv;
${NOISE}
void main() {
  vec2 p = vUv * vec2(1.0, 1.78) * 2.0;
  float t = uTime * 0.18;
  float w = fbm(p + vec2(t, t * 0.4));
  float folds = sin((p.x + p.y * 0.6) * 2.0 + w * 3.0 - t * 2.0);
  vec3 col = mix(uBase, uA, folds * 0.5 + 0.5);
  float sheen = pow(max(0.0, folds), 4.0);
  col = mix(col, uC, sheen * 0.16);
  col = mix(col, uB, smoothstep(0.55, 1.0, w) * 0.3);
  col += (hash(vUv * 1000.0 + uTime) - 0.5) * uGrain;
  gl_FragColor = vec4(col, 1.0);
}`,
};

const col = (hex: string) => new THREE.Color(hex);

const ShaderPlane: React.FC<{ preset: string; colors: string[]; t: number; grain: number }> = ({ preset, colors, t, grain }) => {
  const [base, a, b, c] = colors;
  const uniforms = useMemo(() => ({
    uTime: { value: 0 }, uGrain: { value: grain },
    uBase: { value: col(base) }, uA: { value: col(a) }, uB: { value: col(b) }, uC: { value: col(c ?? "#FFFFFF") },
  }), [base, a, b, c, grain]);
  uniforms.uTime.value = t;
  return (
    <mesh frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial vertexShader={VERT} fragmentShader={FRAG[preset]} uniforms={uniforms} depthWrite={false} />
    </mesh>
  );
};

// glossy clearcoat shapes floating slowly in a soft-lit space
const Glass: React.FC<{ colors: string[]; t: number }> = ({ colors, t }) => {
  const shapes = [
    { geo: <torusKnotGeometry args={[0.9, 0.3, 220, 32]} />, pos: [1.6, 3.2, -2], s: 0.8 },
    { geo: <icosahedronGeometry args={[1, 6]} />, pos: [-2.2, 0.6, -3], s: 0.6 },
    { geo: <torusGeometry args={[0.8, 0.26, 64, 160]} />, pos: [1.8, -2.6, -2.5], s: 0.7 },
  ] as const;
  return (
    <>
      <color attach="background" args={[colors[0]]} />
      <ambientLight intensity={0.9} />
      <directionalLight position={[3, 5, 6]} intensity={2.2} />
      <pointLight position={[-4, -2, 3]} intensity={18} color={colors[3] ?? "#FFFFFF"} />
      {shapes.map((sh, i) => (
        <mesh key={i} position={[sh.pos[0], sh.pos[1] + Math.sin(t * 0.6 + i * 2) * 0.15, sh.pos[2]]}
          rotation={[t * 0.25 + i, t * 0.35 + i * 1.3, 0]} scale={sh.s}>
          {sh.geo}
          <meshPhysicalMaterial color={colors[1 + (i % 2)]} roughness={0.15} metalness={0.1} clearcoat={1} clearcoatRoughness={0.08} sheen={0.6} />
        </mesh>
      ))}
    </>
  );
};

export const ShaderBg: React.FC<{ preset: string; colors: string[]; grain?: number }> = ({ preset, colors, grain = 0.03 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  return (
    <ThreeCanvas width={width} height={height} camera={{ position: [0, 0, 8], fov: 50 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
      {preset === "glass" ? <Glass colors={colors} t={t} /> : <ShaderPlane preset={preset} colors={colors} t={t} grain={grain} />}
    </ThreeCanvas>
  );
};
