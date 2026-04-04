import { Navigate, RouterProvider, createHashRouter } from "react-router-dom";

import { AppShell } from "@/app/app-shell";
import { RenderLabPage } from "@/app/render-lab-page";

const router = createHashRouter([
  { path: "/", element: <AppShell /> },
  { path: "/conversations/:conversationId", element: <AppShell /> },
  { path: "/dev/render-lab", element: <RenderLabPage /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
