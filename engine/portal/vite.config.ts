import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Relative base: works both under the GitHub Pages subpath (/Blink/) and a
// future apex custom domain, with no config change.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  server: {
    watch: {
      // Editors and coding agents stage a write in a dot-prefixed temp dir
      // beside the target file, then rename it into place. A watcher that
      // descends into one of those hits EBUSY on the locked temp file, and
      // Vite re-emits a watcher error as a fatal 'error' event: the dev server
      // exits mid-edit instead of logging a warning. Nothing under src/ is ever
      // named this way, so the pattern cannot hide a real file.
      ignored: ["**/.*.tmpdir", "**/.*.tmpdir/**"],
    },
  },
});
