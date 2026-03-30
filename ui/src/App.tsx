import { Navigate, RouterProvider, createHashRouter } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";

const router = createHashRouter([
  { path: "/", element: <AppShell /> },
  { path: "/conversations/:conversationId", element: <AppShell /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
