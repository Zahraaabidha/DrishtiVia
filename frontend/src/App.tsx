import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout          from "./components/layout/AppLayout";
import DashboardPage      from "./pages/DashboardPage";
import LiveDetectPage     from "./pages/LiveDetectPage";
import ReviewPage         from "./pages/ReviewPage";
import AnalyticsPage      from "./pages/AnalyticsPage";
import VerifyPage         from "./pages/VerifyPage";
import KnowledgeGraphPage from "./pages/KnowledgeGraphPage";
import AgentPage          from "./pages/AgentPage";
import ModelPerformancePage from "./pages/ModelPerformancePage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/"          element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/detect"    element={<LiveDetectPage />} />
        <Route path="/review"    element={<ReviewPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/graph"     element={<KnowledgeGraphPage />} />
        <Route path="/agent"     element={<AgentPage />} />
        <Route path="/verify"    element={<VerifyPage />} />
        <Route path="/models"    element={<ModelPerformancePage />} />
      </Routes>
    </AppLayout>
  );
}
