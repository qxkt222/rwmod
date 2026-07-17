import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  build: {
    outDir: "../static",
    emptyOutDir: true,
    // Code splitting: separate vendor chunks for better caching
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // Put panel modules in separate chunks — loaded on demand
          if (id.includes("/panels/")) {
            const name = id.split("/panels/")[1].split(".")[0];
            return `panel-${name}`;
          }
        },
      },
    },
    // Enable minification with target ES2022
    target: "es2022",
    minify: "esbuild",
    // Generate smaller sourcemaps for production
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
