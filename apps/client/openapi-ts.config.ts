import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../../docs/api/openapi.json",
  output: {
    clean: true,
    path: "src/lib/api-contract",
  },
  plugins: ["@hey-api/typescript", "zod"],
});
