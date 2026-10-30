import { Composition } from "remotion";
import { Reel } from "./Reel";
import type { Props } from "./types";

export const Root: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={{} as Props}
    calculateMetadata={({ props }) => ({
      width: props.style.canvas.width,
      height: props.style.canvas.height,
      fps: props.style.canvas.fps,
      durationInFrames: Math.max(1, Math.round(props.duration * props.style.canvas.fps)),
    })}
  />
);
