import { Composition, staticFile } from "remotion";
import { SentinelDemo, type SentinelDemoProps } from "./SentinelDemo";

const TOTAL_FRAMES = 3600; // 120s @ 30fps
const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

export const RemotionRoot = () => {
  return (
    <Composition
      id="SentinelDemo"
      component={SentinelDemo}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={
        {
          videoSrc: staticFile("demo-recording.webm"),
        } satisfies SentinelDemoProps
      }
    />
  );
};
