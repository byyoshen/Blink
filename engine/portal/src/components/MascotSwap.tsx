/** The mascot pair, cross-faded on theme change: cat on dark, dog on light.
 *
 * Neither image shrinks to nothing on the way out -- a mark that collapses to a
 * point reads as vanishing rather than as one face turning into the other.
 *
 * Shared rather than inlined because the nav mark and the footer both need it.
 * They previously carried hand-copied versions of this markup, and the footer's
 * had already drifted: it still animated from scale-0 after the others were
 * corrected. The theme control is deliberately no longer one of its callers --
 * two mascots in one bar read as duplication; see ThemeGlyph.
 */
export default function MascotSwap({ dark }: { dark: boolean }) {
  const base =
    "absolute h-full w-full rounded-full object-cover transition-all duration-300 ease-out motion-reduce:transition-none";
  return (
    <>
      <img
        src="blink-logo.png"
        alt=""
        className={`${base} ${dark ? "rotate-0 scale-100 opacity-100" : "-rotate-180 scale-50 opacity-0"}`}
      />
      <img
        src="blink-logo-2.png"
        alt=""
        className={`${base} ${dark ? "rotate-180 scale-50 opacity-0" : "rotate-0 scale-100 opacity-100"}`}
      />
    </>
  );
}
