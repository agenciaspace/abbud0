import { Composition } from "remotion";
import { Promo } from "./Promo";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Promo"
        component={Promo}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
