import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import Layout from "./components/Layout";
import CourseDetail from "./pages/CourseDetail";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import ReviewDesk from "./pages/ReviewDesk";
import StudentResult from "./pages/StudentResult";
import VersionComparePage from "./pages/VersionComparePage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout>
              <Dashboard />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/courses/:courseId"
        element={
          <RequireAuth>
            <Layout>
              <CourseDetail />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/reviews/:reviewId"
        element={
          <RequireAuth>
            <ReviewDesk />
          </RequireAuth>
        }
      />
      <Route
        path="/submissions/:submissionId/result"
        element={
          <RequireAuth>
            <Layout>
              <StudentResult />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/submissions/:submissionId/compare/:fromVersionId/:toVersionId"
        element={
          <RequireAuth>
            <Layout>
              <VersionComparePage />
            </Layout>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
