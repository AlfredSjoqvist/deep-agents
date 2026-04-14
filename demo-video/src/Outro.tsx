import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
  Sequence,
} from "remotion";

const SPONSORS = [
  { name: "Anthropic", role: "LLM" },
  { name: "Auth0", role: "Identity" },
  { name: "Ghost DB", role: "Database" },
  { name: "Bland AI", role: "Phone Calls" },
  { name: "Airbyte", role: "Ingestion" },
  { name: "Aerospike", role: "Cache/Search" },
  { name: "Senso.ai", role: "Context Store" },
  { name: "Overmind", role: "Tracing" },
  { name: "Truefoundry", role: "AI Gateway" },
  { name: "Macroscope", role: "Code Review" },
];

type SponsorCardProps = {
  name: string;
  role: string;
  delayFrames: number;
};

const SponsorCard = ({ name, role, delayFrames }: SponsorCardProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 20, stiffness: 180 },
  });

  const opacity = interpolate(progress, [0, 1], [0, 1]);
  const translateY = interpolate(progress, [0, 1], [20, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        backgroundColor: "rgba(0,255,65,0.06)",
        border: "1px solid rgba(0,255,65,0.25)",
        borderRadius: 4,
        padding: "12px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        minWidth: 140,
      }}
    >
      <div
        style={{
          fontFamily: "'Courier New', monospace",
          fontSize: 15,
          fontWeight: 700,
          color: "#ffffff",
          letterSpacing: "0.05em",
        }}
      >
        {name}
      </div>
      <div
        style={{
          fontFamily: "'Courier New', monospace",
          fontSize: 11,
          color: "rgba(0,255,65,0.7)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        {role}
      </div>
    </div>
  );
};

export const Outro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Overall fade in
  const containerOpacity = interpolate(frame, [0, 0.6 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  // "Powered by" label
  const poweredByOpacity = interpolate(frame, [0.2 * fps, 1.0 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Divider line grows
  const lineWidth = interpolate(frame, [0.8 * fps, 1.8 * fps], [0, 900], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // Bottom credits fade
  const creditsOpacity = interpolate(frame, [5 * fps, 7 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const creditsY = interpolate(frame, [5 * fps, 7 * fps], [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        fontFamily: "'Courier New', Courier, monospace",
        overflow: "hidden",
        opacity: containerOpacity,
      }}
    >
      {/* Subtle grid */}
      <AbsoluteFill
        style={{
          opacity: 0.08,
          backgroundImage:
            "linear-gradient(rgba(0,255,65,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,65,0.3) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Corner brackets */}
      {[
        { top: 32, left: 32, borderTop: true, borderLeft: true, borderBottom: false, borderRight: false },
        { top: 32, right: 32, borderTop: true, borderLeft: false, borderBottom: false, borderRight: true },
        { bottom: 32, left: 32, borderTop: false, borderLeft: true, borderBottom: true, borderRight: false },
        { bottom: 32, right: 32, borderTop: false, borderLeft: false, borderBottom: true, borderRight: true },
      ].map((corner, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: corner.top,
            left: corner.left,
            right: corner.right,
            bottom: corner.bottom,
            width: 60,
            height: 60,
            borderTop: corner.borderTop ? "2px solid rgba(0,255,65,0.5)" : undefined,
            borderLeft: corner.borderLeft ? "2px solid rgba(0,255,65,0.5)" : undefined,
            borderBottom: corner.borderBottom ? "2px solid rgba(0,255,65,0.5)" : undefined,
            borderRight: corner.borderRight ? "2px solid rgba(0,255,65,0.5)" : undefined,
          }}
        />
      ))}

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "60px 80px",
          gap: 0,
        }}
      >
        {/* "Powered by" header */}
        <div
          style={{
            fontSize: 16,
            letterSpacing: "0.35em",
            color: "rgba(0,255,65,0.7)",
            textTransform: "uppercase",
            opacity: poweredByOpacity,
            marginBottom: 20,
          }}
        >
          Powered by
        </div>

        {/* Divider */}
        <div
          style={{
            width: lineWidth,
            height: 1,
            backgroundColor: "rgba(0,255,65,0.4)",
            marginBottom: 32,
            boxShadow: "0 0 8px rgba(0,255,65,0.3)",
          }}
        />

        {/* Sponsor grid — 5 per row */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
            justifyContent: "center",
            maxWidth: 900,
          }}
        >
          {SPONSORS.map((sponsor, i) => (
            <SponsorCard
              key={sponsor.name}
              name={sponsor.name}
              role={sponsor.role}
              // Stagger each card by 0.15s
              delayFrames={Math.floor(1.5 * fps + i * 0.15 * fps)}
            />
          ))}
        </div>

        {/* Bottom divider */}
        <div
          style={{
            width: interpolate(frame, [4.5 * fps, 5.5 * fps], [0, 700], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.quad),
            }),
            height: 1,
            backgroundColor: "rgba(255,255,255,0.1)",
            marginTop: 36,
            marginBottom: 28,
          }}
        />

        {/* Credits */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
            opacity: creditsOpacity,
            transform: `translateY(${creditsY}px)`,
          }}
        >
          <div
            style={{
              fontSize: 16,
              color: "rgba(255,255,255,0.6)",
              letterSpacing: "0.08em",
            }}
          >
            Built at Deep Agents Hackathon — March 2026
          </div>
          <div
            style={{
              fontSize: 20,
              color: "#ffffff",
              fontWeight: 700,
              letterSpacing: "0.05em",
            }}
          >
            Arya Teja Rudraraju &amp; Alfred Sjoqvist
          </div>
          {/* Shield icon finale */}
          <div
            style={{
              fontSize: 32,
              marginTop: 8,
              filter: "drop-shadow(0 0 10px rgba(0,255,65,0.6))",
              opacity: interpolate(frame, [7 * fps, 8 * fps], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            🛡️
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
