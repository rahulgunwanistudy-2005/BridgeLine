import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { webConfig } from "./lib/env";
import "./styles/base.css";

async function bootstrap(): Promise<void> {
  if (webConfig.apiMode === "mock") {
    const { startMockServer } = await import("../mock/browser");
    await startMockServer();
  }

  const root = document.getElementById("root");
  if (root === null) {
    throw new Error("Bridgeline root element was not found.");
  }

  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void bootstrap();
