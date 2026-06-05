import "./styles.css";
import { mount } from "svelte";
import App from "./App.svelte";

const target = document.querySelector<HTMLDivElement>("#app");

if (!target) {
  throw new Error("App target #app was not found");
}

mount(App, { target });
