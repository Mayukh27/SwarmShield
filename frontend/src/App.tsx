import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import Targets from "./pages/Targets";
import PatchCenter from "./pages/PatchCenter";
import Vulnerabilities from "./pages/Vulnerabilities";
import Reports from "./pages/Reports";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route element={<DashboardLayout />}>

          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />

          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/agents"
            element={<Agents />}
          />

          <Route
            path="/targets"
            element={<Targets />}
          />

          <Route
            path="/vulnerabilities"
            element={<Vulnerabilities />}
          />

         <Route
  path="/patch-center"
  element={<PatchCenter />}
/>
          <Route
  path="/reports"
  element={<Reports />}
/>
        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default App;