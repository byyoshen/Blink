import { useId } from "react";

/** One sun/moon glyph that morphs between the two states.
 *
 * A cross-fade reads as two pictures trading places. This is a single shape
 * instead: the sun is a filled disc with rays, and a second circle parked clear
 * of the disc slides in to carve the crescent once the rays have withdrawn.
 * Same disc, same centre, so the eye follows one object changing state.
 *
 * The carve is a mask rather than a second shape filled in the button's
 * background colour, because that background changes on hover (bg-card ->
 * bg-paper) and a background-coloured bite would leave a pale disc edge behind
 * on hover. The mask region has to be stated in userSpaceOnUse units: the
 * default region is a percentage of the masked element's own bounding box,
 * which would clip a disc whose mask content sits outside it.
 *
 * Weight is deliberate, because a hairline icon next to the filled mascot mark
 * reads as a drawing rather than as a button. The disc is solid and the rays
 * are short and 2.4 units thick. The moon is the fat crescent: the bite's rim
 * passes through the disc's centre (offset d = 0.94 x disc r, bite r = 0.95 x
 * disc r), which is what keeps the body at full thickness, and the tip angle --
 * the angle at which the two rims cross, acos((R^2 + r^2 - d^2) / 2Rr) -- lands
 * at ~58 deg. Feather's and Lucide's moons sit at 45-49 deg, which at this size
 * narrows into a needle point. Every cap also has to stay inside the viewBox:
 * an icon clipped by its own viewport gets flat-cut ray tips.
 */
export default function ThemeGlyph({ dark }: { dark: boolean }) {
  // The nav button and an open menu row mount this at the same time, so the
  // mask id must be unique per instance. React's useId carries characters that
  // are awkward inside url(#...), hence the strip.
  const maskId = `moon-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-full w-full">
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="24" height="24">
          <rect width="24" height="24" fill="#fff" />
          {/* The bite: parked clear of the disc while the rays are out, slid
              onto it to carve the crescent. Overshoot on the way in, so the
              moon forms with a small snap rather than a glide; the offset still
              stays inside the bite at the peak, so the shape never becomes a
              cookie notch on the way. */}
          <circle
            cx="22.25"
            cy="1.75"
            r="6.46"
            fill="#000"
            className={`transition-transform duration-[520ms] ease-[cubic-bezier(0.34,1.3,0.64,1)] motion-reduce:transition-none ${
              dark ? "[transform:translate(0px,0px)]" : "[transform:translate(-5.72px,5.72px)]"
            }`}
          />
        </mask>
      </defs>
      {/* Rays withdraw into the disc -- scaled about the glyph's centre, which
          an SVG element only honours once transform-box says so. */}
      <g
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        className={`[transform-box:view-box] [transform-origin:12px_12px] transition-[transform,opacity] duration-[420ms] ease-[cubic-bezier(0.4,0,0.2,1)] motion-reduce:transition-none ${
          dark ? "[transform:scale(1)] opacity-100" : "[transform:scale(0.5)] opacity-0"
        }`}
      >
        <path d="M20.7 12h1.8M12 20.7v1.8M3.3 12h-1.8M12 3.3v-1.8M18.15 18.15l1.27 1.27M5.85 5.85l-1.27-1.27M18.15 5.85l1.27-1.27M5.85 18.15l-1.27 1.27" />
      </g>
      <circle cx="12" cy="12" r="6.8" fill="currentColor" mask={`url(#${maskId})`} />
    </svg>
  );
}
