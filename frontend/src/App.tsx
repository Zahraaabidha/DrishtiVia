import { Routes, Route } from "react-router-dom";
import AppLayout            from "./components/layout/AppLayout";
import LandingPage          from "./pages/LandingPage";
import DashboardPage        from "./pages/DashboardPage";
import LiveDetectPage       from "./pages/LiveDetectPage";
import ReviewPage           from "./pages/ReviewPage";
import AnalyticsPage        from "./pages/AnalyticsPage";
import VerifyPage           from "./pages/VerifyPage";
import KnowledgeGraphPage   from "./pages/KnowledgeGraphPage";
import AgentPage            from "./pages/AgentPage";
import ModelPerformancePage from "./pages/ModelPerformancePage";

export default function App() {
  return (
    <Routes>
      {/* Landing page — no sidebar/AppLayout */}
      <Route path="/" element={<LandingPage />} />

      {/* Dashboard routes — wrapped in AppLayout with sidebar */}
      <Route path="/*" element={
        <AppLayout>
          <Routes>
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
      } />
    </Routes>
  );
}
