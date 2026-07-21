export type ApiMode = "mock" | "real";

export interface WebConfig {
  apiMode: ApiMode;
  apiBaseUrl: string;
  isTestRuntime: boolean;
}

function readApiMode(value: string | undefined): ApiMode {
  if (value === undefined || value === "mock") {
    return "mock";
  }
  if (value === "real") {
    return "real";
  }
  throw new Error(`VITE_API_MODE must be "mock" or "real", received "${value}".`);
}

export const webConfig: WebConfig = {
  apiMode: readApiMode(import.meta.env.VITE_API_MODE),
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  isTestRuntime: import.meta.env.MODE === "test",
};
