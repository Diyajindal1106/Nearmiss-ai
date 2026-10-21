import { Route, Routes } from "react-router-dom";
import { ConfigProvider } from "./ConfigContext.jsx";
import Layout from "./components/Layout.jsx";
import Landing from "./pages/Landing.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ReportForm from "./pages/ReportForm.jsx";
import ReportDetail from "./pages/ReportDetail.jsx";
import CampusMap from "./pages/CampusMap.jsx";

export default function App() {
  return (
    <ConfigProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/report" element={<ReportForm />} />
          <Route path="/reports/:id" element={<ReportDetail />} />
          <Route path="/map" element={<CampusMap />} />
          <Route path="*" element={<div className="card"><h2>Page not found</h2></div>} />
        </Route>
      </Routes>
    </ConfigProvider>
  );
}
