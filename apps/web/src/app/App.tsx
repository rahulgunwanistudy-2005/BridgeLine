import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { RunPage } from "../features/pipeline/RunPage";
import { UploadPage } from "../features/pipeline/UploadPage";
import { ReviewPage } from "../features/review/ReviewPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { BriefPage } from "../features/brief/BriefPage";
import { FoundationPage } from "./FoundationPage";
import { RulesPage } from "../features/rules/RulesPage";
import { JudgeModePage } from "../features/judge/JudgeModePage";

const router = createBrowserRouter([
  { path: "/", element: <FoundationPage /> },
  { path: "/judge", element: <JudgeModePage /> },
  {
    element: <AppShell />,
    children: [
      { path: "/upload", element: <UploadPage /> },
      { path: "/runs/:runId", element: <RunPage /> },
      { path: "/runs/:runId/review", element: <ReviewPage /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/briefs/:teacherId", element: <BriefPage /> },
      { path: "/my-briefs", element: <BriefPage /> },
      { path: "/rules", element: <RulesPage /> },
    ],
  },
  { path: "*", element: <FoundationPage /> },
]);

export function App(): React.JSX.Element {
  return <RouterProvider router={router} />;
}
