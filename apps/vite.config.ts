import clientConfig from "./client/vite.config";

export default {
  ...clientConfig,
  root: "client",
  test: {
    ...clientConfig.test,
    environmentOptions: {
      jsdom: {
        url: "http://localhost:5173/",
      },
    },
  },
};
