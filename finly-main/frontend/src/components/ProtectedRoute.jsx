import { Navigate } from "react-router-dom";

// BUG-05: also verify locally-cached user_data integrity so we avoid
// flashing the authenticated shell when the stored session is corrupt.
export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem("auth_token");
  if (!token) return <Navigate to="/login" replace />;
  try {
    const raw = localStorage.getItem("user_data") || "{}";
    const u = JSON.parse(raw);
    if (!u || !u.id) return <Navigate to="/login" replace />;
  } catch {
    return <Navigate to="/login" replace />;
  }
  return children;
}
