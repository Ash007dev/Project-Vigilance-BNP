import { BrowserRouter, Route, Routes, useNavigate, useParams } from "react-router-dom";

import UploadPage from "./pages/UploadPage";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Investigations from "./pages/Investigations";
import Investigation from "./Investigation";


function InvestigationRoute() {
  const navigate = useNavigate();
  const { accountId } = useParams();

  if (!accountId) {
    return <Investigations />;
  }

  return (
    <Investigation
      account={accountId}
      onBack={() => navigate("/investigations")}
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route
          path="/"
          element={<UploadPage />}
        />

        <Route
          path="/dashboard"
          element={<Dashboard />}
        />

        <Route
          path="/alerts"
          element={<Alerts />}
        />

        <Route
          path="/investigations"
          element={<Investigations />}
        />

        <Route
          path="/investigations/:accountId"
          element={<InvestigationRoute />}
        />

      </Routes>
    </BrowserRouter>
  );
}
