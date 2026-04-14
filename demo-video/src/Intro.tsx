import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";

export const Intro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background grid fade in
  const bgOpacity = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Shield + title spring entrance
  const shieldScale = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 1 },
    durationInFrames: 1.5 * fps,
  });

  const shieldOpacity = interpolate(frame, [0, 0.4 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Title slides up after shield
  const titleY = interpolate(frame, [0.3 * fps, 1.2 * fps], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  const titleOpacity = interpolate(frame, [0.3 * fps, 1.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtitle fades in after title
  const subtitleOpacity = interpolate(frame, [1.2 * fps, 2.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const subtitleY = interpolate(frame, [1.2 * fps, 2.2 * fps], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // Badge slides in last
  const badgeOpacity = interpolate(frame, [2.2 * fps, 3.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const badgeScale = spring({
    frame: frame - 2.2 * fps,
    fps,
    config: { damping: 20, stiffness: 200 },
  });

  // Scanline effect progress
  const scanlineProgress = interpolate(frame, [0, 5 * fps], [0, 100], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        fontFamily: "'Courier New', Courier, monospace",
        overflow: "hidden",
      }}
    >
      {/* Grid background */}
      <AbsoluteFill
        style={{
          opacity: bgOpacity * 0.15,
          backgroundImage:
            "linear-gradient(rgba(0,255,65,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,65,0.3) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Scanline sweep */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(transparent ${scanlineProgress - 2}%, rgba(0,255,65,0.08) ${scanlineProgress}%, transparent ${scanlineProgress + 2}%)`,
          pointerEvents: "none",
        }}
      />

      {/* Corner brackets */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 40,
          width: 80,
          height: 80,
          borderTop: "2px solid rgba(0,255,65,0.6)",
          borderLeft: "2px solid rgba(0,255,65,0.6)",
          opacity: bgOpacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 40,
          right: 40,
          width: 80,
          height: 80,
          borderTop: "2px solid rgba(0,255,65,0.6)",
          borderRight: "2px solid rgba(0,255,65,0.6)",
          opacity: bgOpacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 40,
          width: 80,
          height: 80,
          borderBottom: "2px solid rgba(0,255,65,0.6)",
          borderLeft: "2px solid rgba(0,255,65,0.6)",
          opacity: bgOpacity,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 40,
          width: 80,
          height: 80,
          borderBottom: "2px solid rgba(0,255,65,0.6)",
          borderRight: "2px solid rgba(0,255,65,0.6)",
          opacity: bgOpacity,
        }}
      />

      {/* Center content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 0,
        }}
      >
        {/* Shield icon */}
        <div
          style={{
            fontSize: 96,
            opacity: shieldOpacity,
            transform: `scale(${shieldScale})`,
            lineHeight: 1,
            marginBottom: 24,
            filter: "drop-shadow(0 0 20px rgba(0,255,65,0.8))",
          }}
        >
          🛡️
        </div>

        {/* SENTINEL title */}
        <div
          style={{
            fontSize: 96,
            fontWeight: 900,
            letterSpacing: "0.3em",
            color: "#ffffff",
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            textShadow: "0 0 30px rgba(0,255,65,0.5), 0 0 60px rgba(0,255,65,0.2)",
            fontFamily: "'Courier New', monospace",
          }}
        >
          SENTINEL SQUARE
        </div>

        {/* Green accent line */}
        <div
          style={{
            width: interpolate(frame, [1.0 * fps, 1.8 * fps], [0, 600], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.quad),
            }),
            height: 3,
            backgroundColor: "#00ff41",
            marginTop: 16,
            marginBottom: 28,
            boxShadow: "0 0 12px rgba(0,255,65,0.8)",
          }}
        />

        {/* Subtitle */}
        <div
          style={{
            fontSize: 28,
            color: "#00ff41",
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
            letterSpacing: "0.1em",
            fontFamily: "'Courier New', monospace",
            textTransform: "uppercase",
          }}
        >
          Autonomous Breach Response Agent
        </div>

        {/* Hackathon badge */}
        <div
          style={{
            marginTop: 40,
            opacity: badgeOpacity,
            transform: `scale(${badgeScale})`,
            backgroundColor: "rgba(0,255,65,0.12)",
            border: "1px solid rgba(0,255,65,0.5)",
            borderRadius: 4,
            padding: "10px 28px",
            fontSize: 18,
            color: "rgba(255,255,255,0.8)",
            letterSpacing: "0.08em",
            fontFamily: "'Courier New', monospace",
          }}
        >
          Deep Agents Hackathon — March 2026
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
