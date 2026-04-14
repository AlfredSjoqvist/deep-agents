import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
import { Video } from "@remotion/media";

// Props for the demo video segment
export type DemoVideoProps = {
  // Path to the screen recording — drop your .mp4 here
  // e.g., staticFile("demo-recording.mp4") or an absolute URL
  videoSrc: string | null;
};

const LiveBadge = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Pulse the dot every second
  const pulse = interpolate(
    Math.sin((frame / fps) * Math.PI * 2),
    [-1, 1],
    [0.4, 1.0]
  );

  const badgeOpacity = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: 0.5 * fps,
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 36,
        left: 48,
        display: "flex",
        alignItems: "center",
        gap: 10,
        backgroundColor: "rgba(0,0,0,0.75)",
        border: "1px solid rgba(0,255,65,0.6)",
        borderRadius: 4,
        padding: "8px 18px",
        fontFamily: "'Courier New', monospace",
        opacity: badgeOpacity,
      }}
    >
      {/* Pulsing dot */}
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          backgroundColor: "#00ff41",
          boxShadow: "0 0 8px rgba(0,255,65,0.9)",
          opacity: pulse,
        }}
      />
      <span
        style={{
          color: "#00ff41",
          fontSize: 16,
          fontWeight: 700,
          letterSpacing: "0.15em",
        }}
      >
        LIVE DEMO
      </span>
      <span
        style={{
          color: "rgba(255,255,255,0.5)",
          fontSize: 14,
          letterSpacing: "0.05em",
          marginLeft: 4,
        }}
      >
        · Sentinel Breach Response
      </span>
    </div>
  );
};

const TimecodeDisplay = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalSeconds = Math.floor(frame / fps);
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  const frames = (frame % fps).toString().padStart(2, "0");

  return (
    <div
      style={{
        position: "absolute",
        bottom: 36,
        right: 48,
        fontFamily: "'Courier New', monospace",
        fontSize: 14,
        color: "rgba(255,255,255,0.4)",
        letterSpacing: "0.1em",
      }}
    >
      {minutes}:{seconds}:{frames}
    </div>
  );
};

export const DemoVideo = ({ videoSrc }: DemoVideoProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade in on entry
  const fadeIn = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        opacity: fadeIn,
      }}
    >
      {videoSrc ? (
        // Real recording — will fill the frame
        <Video
          src={videoSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
          }}
        />
      ) : (
        // Placeholder shown until you drop in a recording
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#0a0a0a",
            backgroundImage:
              "linear-gradient(rgba(0,255,65,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,65,0.04) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        >
          <div
            style={{
              fontFamily: "'Courier New', monospace",
              color: "rgba(0,255,65,0.3)",
              fontSize: 18,
              letterSpacing: "0.2em",
              textAlign: "center",
              lineHeight: 2.5,
            }}
          >
            <div style={{ fontSize: 48, marginBottom: 16 }}>📹</div>
            <div>[ DEMO RECORDING PLACEHOLDER ]</div>
            <div style={{ fontSize: 13, marginTop: 12, color: "rgba(255,255,255,0.2)" }}>
              Drop demo-recording.mp4 into /public/
            </div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.2)" }}>
              then set videoSrc to staticFile("demo-recording.mp4")
            </div>
          </div>
        </AbsoluteFill>
      )}

      {/* HUD overlays always shown */}
      <LiveBadge />
      <TimecodeDisplay />

      {/* Top-right watermark */}
      <div
        style={{
          position: "absolute",
          top: 24,
          right: 36,
          fontFamily: "'Courier New', monospace",
          fontSize: 13,
          color: "rgba(0,255,65,0.35)",
          letterSpacing: "0.15em",
        }}
      >
        SENTINEL v1.0
      </div>
    </AbsoluteFill>
  );
};
