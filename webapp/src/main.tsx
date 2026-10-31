import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/saira";
import "./tank.css";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
