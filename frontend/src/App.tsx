import { BrowserRouter, Routes, Route } from "react-router-dom";

import UploadPage from "./pages/UploadPage";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Investigations from "./pages/Investigations";

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
          element={<Investigations />}
        />

      </Routes>
    </BrowserRouter>
  );
}