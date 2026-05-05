import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
const inter = { fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" };
const jetbrains = { fontFamily: "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace" };

const COLORS = {
  bg: "#0a0a0a",
  surface: "#141414",
  border: "#262626",
  text: "#f5f5f5",
  text2: "#999",
  accent: "#4ADE80",
  accentDim: "rgba(74, 222, 128, 0.18)",
};

const PALETTE = [
  "#E91E63", "#4CAF50", "#2196F3", "#FF9800", "#9C27B0",
  "#00BCD4", "#F44336", "#8BC34A", "#3F51B5", "#FFEB3B",
  "#795548", "#607D8B", "#FF5722", "#009688", "#673AB7",
];

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

export const Promo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: COLORS.bg, fontFamily: inter.fontFamily }}>
      <Grain />
      <Sequence from={0} durationInFrames={75}>
        <SceneIntro />
      </Sequence>
      <Sequence from={75} durationInFrames={105}>
        <SceneTitle />
      </Sequence>
      <Sequence from={180} durationInFrames={120}>
        <ScenePDF />
      </Sequence>
      <Sequence from={300} durationInFrames={120}>
        <SceneProcessing />
      </Sequence>
      <Sequence from={420} durationInFrames={120}>
        <SceneMap />
      </Sequence>
      <Sequence from={540} durationInFrames={60}>
        <SceneOutro />
      </Sequence>
    </AbsoluteFill>
  );
};

const Grain: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.04, mixBlendMode: "overlay" }}>
    <svg width="100%" height="100%">
      <filter id="n">
        <feTurbulence baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#n)" />
    </svg>
  </AbsoluteFill>
);

const SceneIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });
  const opacity = interpolate(frame, [0, 20, 55, 75], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity }}>
      <div style={{ transform: `scale(${0.6 + scale * 0.4})`, display: "flex", alignItems: "center", gap: 24 }}>
        <Logo size={120} />
        <div style={{ width: 2, height: 80, background: COLORS.border }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 14, letterSpacing: 4, color: COLORS.text2, textTransform: "uppercase", fontWeight: 500 }}>
            Paisagismo Tecnico
          </div>
          <div style={{ fontSize: 32, color: COLORS.text, fontWeight: 600, letterSpacing: -0.5 }}>
            Mapa de Vegetacao
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Logo: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 120 120">
    <defs>
      <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#4ADE80" />
        <stop offset="100%" stopColor="#22C55E" />
      </linearGradient>
    </defs>
    <rect x="6" y="6" width="108" height="108" rx="26" fill="url(#lg)" />
    <g transform="translate(60 60)" fill="none" stroke="#0a0a0a" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M 0 -28 C -14 -28 -22 -16 -18 -2 C -28 -2 -28 14 -16 18 C -16 26 -8 28 0 26 C 8 28 16 26 16 18 C 28 14 28 -2 18 -2 C 22 -16 14 -28 0 -28 Z" fill="#0a0a0a" fillOpacity="0.15" />
      <path d="M 0 -22 L 0 28" />
      <path d="M 0 8 L -10 -2" />
      <path d="M 0 8 L 10 -2" />
    </g>
  </svg>
);

const SceneTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const wordOpacity = (delay: number) =>
    interpolate(frame, [delay, delay + 12], [0, 1], { extrapolateRight: "clamp" });
  const wordY = (delay: number) =>
    interpolate(spring({ frame: frame - delay, fps, config: { damping: 15 } }), [0, 1], [40, 0]);
  const fadeOut = interpolate(frame, [85, 105], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: fadeOut }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 18, letterSpacing: 5, color: COLORS.accent, textTransform: "uppercase", fontWeight: 600, marginBottom: 28, opacity: wordOpacity(0) }}>
          Sem trabalho manual.
        </div>
        <div style={{ fontSize: 96, fontWeight: 700, letterSpacing: -3, color: COLORS.text, lineHeight: 1.05 }}>
          <div style={{ opacity: wordOpacity(8), transform: `translateY(${wordY(8)}px)` }}>
            Do PDF do projeto
          </div>
          <div style={{ opacity: wordOpacity(22), transform: `translateY(${wordY(22)}px)`, color: COLORS.accent }}>
            ao mapa interativo.
          </div>
        </div>
        <div style={{ fontSize: 20, color: COLORS.text2, marginTop: 36, fontFamily: jetbrains.fontFamily, letterSpacing: 0, opacity: wordOpacity(50) }}>
          $ mapa-vegetacao --auto
        </div>
      </div>
    </AbsoluteFill>
  );
};

const ScenePDF: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = spring({ frame, fps, config: { damping: 18, stiffness: 120 } });
  const slideOut = interpolate(frame, [100, 120], [0, -120], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [100, 120], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const labelOpacity = interpolate(frame, [20, 40], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity, transform: `translateY(${slideOut}px)` }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 28 }}>
        <div style={{ fontSize: 14, letterSpacing: 3, color: COLORS.text2, textTransform: "uppercase", opacity: labelOpacity }}>
          01 &nbsp;&middot;&nbsp; Envie o PDF
        </div>
        <div style={{ position: "relative", width: 360, height: 480 }}>
          <DropZone />
          <div style={{ position: "absolute", inset: 0, transform: `translateY(${interpolate(drop, [0, 1], [-380, 0])}px) rotate(${interpolate(drop, [0, 1], [-8, 0])}deg)` }}>
            <PDFCard />
          </div>
        </div>
        <div style={{ fontSize: 16, color: COLORS.text2, opacity: labelOpacity }}>
          projeto-paisagismo.pdf <span style={{ color: COLORS.accent }}>&middot; 4.2 MB</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const DropZone: React.FC = () => (
  <div
    style={{
      width: "100%",
      height: "100%",
      border: `2px dashed ${COLORS.border}`,
      borderRadius: 24,
      background: COLORS.surface,
    }}
  />
);

const PDFCard: React.FC = () => (
  <div
    style={{
      width: "100%",
      height: "100%",
      background: "#fafafa",
      borderRadius: 20,
      boxShadow: "0 30px 80px rgba(0,0,0,0.6), 0 4px 16px rgba(0,0,0,0.4)",
      padding: 28,
      display: "flex",
      flexDirection: "column",
      gap: 10,
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#E91E63", letterSpacing: 2 }}>PDF</div>
      <div style={{ fontSize: 9, color: "#999", letterSpacing: 1 }}>R00 &middot; 03.2026</div>
    </div>
    <div style={{ height: 2, background: "#222" }} />
    <div style={{ fontSize: 10, fontWeight: 700, color: "#222", letterSpacing: 1 }}>LEGENDA DE PLANTIO</div>
    {Array.from({ length: 14 }).map((_, i) => (
      <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: PALETTE[i % PALETTE.length] }} />
        <div style={{ height: 5, flex: 1, background: "#e5e5e5", borderRadius: 2 }} />
        <div style={{ height: 5, width: 18, background: "#ccc", borderRadius: 2 }} />
      </div>
    ))}
  </div>
);

const SceneProcessing: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, 100, 120], [0, 1, 1, 0]);
  const scan = interpolate(frame, [0, 90], [0, 1], { extrapolateRight: "clamp" });
  const labelOpacity = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" });

  const detections = 326;
  const counter = Math.floor(interpolate(frame, [20, 95], [0, detections], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 28 }}>
        <div style={{ fontSize: 14, letterSpacing: 3, color: COLORS.text2, textTransform: "uppercase", opacity: labelOpacity }}>
          02 &nbsp;&middot;&nbsp; Identificacao automatica
        </div>
        <div
          style={{
            position: "relative",
            width: 720,
            height: 480,
            background: COLORS.surface,
            borderRadius: 20,
            border: `1px solid ${COLORS.border}`,
            overflow: "hidden",
          }}
        >
          <BlueprintBackground />
          <Scanline progress={scan} />
          <DetectionDots frame={frame} />
        </div>
        <div style={{ display: "flex", gap: 48, fontFamily: jetbrains.fontFamily }}>
          <Stat label="ESPECIES" value={counter} />
          <Stat label="ARVORES" value={Math.floor(counter * 0.42)} />
          <Stat label="ARBUSTOS" value={Math.floor(counter * 0.31)} />
          <Stat label="FORRACOES" value={Math.floor(counter * 0.27)} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Stat: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
    <div style={{ fontSize: 36, fontWeight: 700, color: COLORS.text, letterSpacing: -1 }}>
      {value.toString().padStart(3, "0")}
    </div>
    <div style={{ fontSize: 11, letterSpacing: 2, color: COLORS.text2 }}>{label}</div>
  </div>
);

const BlueprintBackground: React.FC = () => (
  <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.4 }}>
    <defs>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke={COLORS.border} strokeWidth="0.5" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#grid)" />
    <path d="M 100 100 L 620 100 L 620 380 L 100 380 Z" fill="none" stroke={COLORS.text2} strokeWidth="1.5" strokeOpacity="0.5" />
    <path d="M 200 100 L 200 380" stroke={COLORS.text2} strokeWidth="1" strokeOpacity="0.3" strokeDasharray="4 4" />
    <path d="M 100 240 L 620 240" stroke={COLORS.text2} strokeWidth="1" strokeOpacity="0.3" strokeDasharray="4 4" />
  </svg>
);

const Scanline: React.FC<{ progress: number }> = ({ progress }) => {
  const x = interpolate(progress, [0, 1], [0, 720]);
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: x - 60,
          top: 0,
          width: 60,
          height: "100%",
          background: `linear-gradient(90deg, transparent, ${COLORS.accentDim})`,
        }}
      />
      <div style={{ position: "absolute", left: x, top: 0, width: 2, height: "100%", background: COLORS.accent, boxShadow: `0 0 20px ${COLORS.accent}` }} />
    </>
  );
};

const DETECTION_POINTS = Array.from({ length: 80 }).map((_, i) => {
  const seed = i * 9301 + 49297;
  const r1 = ((seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const r2 = (((seed * 2) * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  return {
    x: 110 + r1 * 500,
    y: 110 + r2 * 260,
    color: PALETTE[i % PALETTE.length],
    delay: i * 1.1,
  };
});

const DetectionDots: React.FC<{ frame: number }> = ({ frame }) => {
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }}>
      {DETECTION_POINTS.map((p, i) => {
        const t = Math.max(0, Math.min(1, (frame - p.delay) / 8));
        const scale = easeOut(t);
        if (scale === 0) return null;
        return (
          <g key={i} transform={`translate(${p.x} ${p.y}) scale(${scale})`}>
            <circle r="8" fill={p.color} fillOpacity="0.7" />
            <circle r="4" fill={p.color} />
          </g>
        );
      })}
    </svg>
  );
};

const SceneMap: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, 100, 120], [0, 1, 1, 0]);
  const scale = spring({ frame, fps: 30, config: { damping: 16 } });
  const labelOpacity = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24 }}>
        <div style={{ fontSize: 14, letterSpacing: 3, color: COLORS.text2, textTransform: "uppercase", opacity: labelOpacity }}>
          03 &nbsp;&middot;&nbsp; Mapa interativo + apresentacao
        </div>
        <div style={{ display: "flex", gap: 24, transform: `scale(${0.85 + scale * 0.15})` }}>
          <DeliverableCard kind="html" frame={frame} />
          <DeliverableCard kind="pdf" frame={frame} />
        </div>
        <div style={{ fontSize: 18, color: COLORS.text2, opacity: labelOpacity, fontFamily: jetbrains.fontFamily }}>
          HTML &middot; PNG &middot; PDF executivo
        </div>
      </div>
    </AbsoluteFill>
  );
};

const DeliverableCard: React.FC<{ kind: "html" | "pdf"; frame: number }> = ({ kind, frame }) => {
  const isHtml = kind === "html";
  const tooltipOpacity = isHtml ? interpolate(frame, [40, 55, 90, 100], [0, 1, 1, 0]) : 0;
  return (
    <div
      style={{
        width: 540,
        height: 380,
        background: isHtml ? "#111" : "#fff",
        borderRadius: 18,
        border: `1px solid ${COLORS.border}`,
        overflow: "hidden",
        position: "relative",
        boxShadow: "0 30px 80px rgba(0,0,0,0.6)",
      }}
    >
      <div
        style={{
          height: 32,
          background: isHtml ? "#1a1a1a" : "#f5f5f5",
          borderBottom: `1px solid ${isHtml ? "#222" : "#e5e5e5"}`,
          display: "flex",
          alignItems: "center",
          paddingLeft: 12,
          gap: 6,
        }}
      >
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#febc2e" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
        <div style={{ marginLeft: 12, fontSize: 11, color: isHtml ? "#666" : "#999", fontFamily: jetbrains.fontFamily }}>
          {isHtml ? "mapa-interativo.html" : "apresentacao.pdf"}
        </div>
      </div>
      {isHtml ? <MapPreview frame={frame} /> : <PDFPreview frame={frame} />}
      {isHtml ? (
        <div
          style={{
            position: "absolute",
            top: 110,
            left: 220,
            background: "#fff",
            color: "#111",
            padding: "10px 14px",
            borderRadius: 10,
            fontSize: 12,
            fontWeight: 600,
            opacity: tooltipOpacity,
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div style={{ width: 28, height: 28, borderRadius: 6, background: PALETTE[1] }} />
          <div>
            <div>Tibouchina granulosa</div>
            <div style={{ fontSize: 10, color: "#666", fontWeight: 400, marginTop: 2 }}>Quaresmeira &middot; 12 itens</div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

const MapPreview: React.FC<{ frame: number }> = ({ frame }) => {
  return (
    <svg width="100%" height="348" viewBox="0 0 540 348" style={{ background: "#0d0d0d" }}>
      <defs>
        <pattern id="g2" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#1f1f1f" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="540" height="348" fill="url(#g2)" />
      <path d="M 60 60 L 480 60 L 480 288 L 60 288 Z" fill="none" stroke="#333" strokeWidth="1" />
      {DETECTION_POINTS.slice(0, 60).map((p, i) => {
        const x = 70 + ((p.x - 110) / 500) * 400;
        const y = 70 + ((p.y - 110) / 260) * 208;
        const t = Math.max(0, Math.min(1, (frame - 5) / 20));
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={6} fill={p.color} fillOpacity={0.7 * t} />
            <circle cx={x} cy={y} r={3} fill={p.color} fillOpacity={t} />
          </g>
        );
      })}
    </svg>
  );
};

const PDFPreview: React.FC<{ frame: number }> = ({ frame }) => {
  const reveal = interpolate(frame, [10, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ padding: "24px 32px", color: "#111", fontFamily: inter.fontFamily }}>
      <div style={{ fontSize: 9, letterSpacing: 2, color: "#999", marginBottom: 8 }}>APRESENTACAO EXECUTIVA</div>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Tibouchina granulosa</div>
      <div style={{ fontSize: 12, color: "#666", marginBottom: 16 }}>Quaresmeira &middot; Arvore</div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <div style={{ width: 130, height: 130, background: "#e8e8e8", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 40 }}>&#127794;</div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            ["Quantidade", "12"],
            ["Cor no mapa", null],
            ["Fonte", "Lorenzi (2008)"],
          ].map(([k, v], i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #eee", paddingBottom: 6, opacity: reveal }}>
              <span style={{ fontSize: 11, color: "#666" }}>{k}</span>
              {v ? (
                <span style={{ fontSize: 11, fontWeight: 600 }}>{v}</span>
              ) : (
                <div style={{ width: 18, height: 18, borderRadius: 4, background: PALETTE[1] }} />
              )}
            </div>
          ))}
        </div>
      </div>
      <div style={{ fontSize: 10, color: "#999", lineHeight: 1.5 }}>
        Especie nativa do Brasil, ornamental, floracao roxa intensa de janeiro a abril.
      </div>
    </div>
  );
};

const SceneOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const ctaY = interpolate(spring({ frame: frame - 18, fps, config: { damping: 16 } }), [0, 1], [20, 0]);
  const ctaOpacity = interpolate(frame, [18, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        background: `radial-gradient(ellipse 60% 50% at 50% 50%, ${COLORS.accentDim}, transparent 70%), ${COLORS.bg}`,
        opacity: fadeIn,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 32, transform: `scale(${0.9 + scale * 0.1})` }}>
        <Logo size={96} />
        <div style={{ fontSize: 64, fontWeight: 700, color: COLORS.text, letterSpacing: -2, textAlign: "center" }}>
          Mapa de Vegetacao
        </div>
        <div
          style={{
            opacity: ctaOpacity,
            transform: `translateY(${ctaY}px)`,
            background: COLORS.accent,
            color: COLORS.bg,
            padding: "16px 36px",
            borderRadius: 12,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: 2,
            textTransform: "uppercase",
            fontFamily: jetbrains.fontFamily,
          }}
        >
          Abrir o app &nbsp;&rarr;
        </div>
      </div>
    </AbsoluteFill>
  );
};
