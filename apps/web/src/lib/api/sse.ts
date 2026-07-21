import type { PipelineStatusEvent } from "../types/generated";

export async function consumePipelineEvents(
  response: Response,
  onEvent: (event: PipelineStatusEvent) => void,
): Promise<void> {
  if (!response.ok) {
    throw new Error(`Pipeline stream failed with HTTP ${response.status}.`);
  }
  if (response.body === null) {
    throw new Error("Pipeline stream response did not include a body.");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += value;
    const messages = buffer.split("\n\n");
    buffer = messages.pop() ?? "";
    for (const message of messages) {
      const data = message
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data.length > 0) {
        onEvent(JSON.parse(data) as PipelineStatusEvent);
      }
    }
  }
}
