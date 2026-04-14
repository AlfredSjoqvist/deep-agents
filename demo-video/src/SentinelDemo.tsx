import { AbsoluteFill, Series, useVideoConfig } from "remotion";
import { Intro } from "./Intro";
import { DemoVideo } from "./DemoVideo";
import { Outro } from "./Outro";

// Total: 3600 frames at 30fps = 120s
// Intro:      frames 0   – 150   (5s)
// Demo:       frames 150 – 3300  (105s)
// Outro:      frames 3300 – 3600 (10s)

const INTRO_DURATION = 150; // 5s × 30fps
const DEMO_DURATION = 3150; // 105s × 30fps
const OUTRO_DURATION = 300; // 10s × 30fps

export type SentinelDemoProps = {
  // Swap null → staticFile("demo-recording.mp4") once you have the file
  videoSrc: string | null;
};

export const SentinelDemo = ({ videoSrc }: SentinelDemoProps) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <Series>
        <Series.Sequence durationInFrames={INTRO_DURATION}>
          <Intro />
        </Series.Sequence>

        <Series.Sequence durationInFrames={DEMO_DURATION}>
          <DemoVideo videoSrc={videoSrc} />
        </Series.Sequence>

        <Series.Sequence durationInFrames={OUTRO_DURATION}>
          <Outro />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
