import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import PatientList from './pages/PatientList';
import PatientDetail from './pages/PatientDetail';
import ModelDashboard from './pages/ModelDashboard';
import Login from './pages/Login';
import { useAuthStore } from './stores/authStore';

function App() {
  const { isAuthenticated } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<Navigate to="/patients" replace />} />
          <Route path="patients" element={<PatientList />} />
          <Route path="patients/:patientId" element={<PatientDetail />} />
          <Route path="model-performance" element={<ModelDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
