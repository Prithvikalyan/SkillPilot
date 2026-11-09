import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import TutorPage from "./pages/TutorPage";
import RoadmapPage from "./pages/RoadmapPage";
import { EmptyState } from "./components/ui";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/tutor" replace />} />
        <Route path="tutor" element={<TutorPage />} />
        <Route path="roadmap" element={<RoadmapPage />} />
        <Route path="*" element={<div className="p-8"><EmptyState title="Page not found">Use the navigation to open the Tutor or the Roadmap.</EmptyState></div>} />
      </Route>
    </Routes>
  );
}
