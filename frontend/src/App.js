import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate,
    useLocation,
} from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

// Old Components
import Monitor from './pages/Monitor';
import Calibration from './pages/Calibration';
import Evidence from './pages/Evidence';
import Admin from './pages/Admin';
import Overview from './pages/Overview';
import Casebook from './pages/Casebook';
import CasePage from './pages/CasePage';
import DatasetLibrary from './pages/DatasetLibrary';
import Registry from './pages/Registry';
import ProjectGuide from './pages/ProjectGuide';

// New Pages
import Auth from './pages/Auth';
import RoleSelection from './pages/RoleSelection';
import UserDashboard from './pages/UserDashboard';
import RTODashboard from './pages/RTODashboard';
import GovernmentAnalytics from './pages/GovernmentAnalytics';
import UserProfile from './pages/UserProfile';

import './App.css';
import './Workspace.css';
import './Experience.css';

const HomeRedirect = () => {
    const { user } = useAuth();
    if (!user) return <RoleSelection />;

    if (user.role === 'RTO' || user.role === 'ADMIN') return <Navigate to="/rto" />;
    if (user.role === 'GOVT') return <Navigate to="/government" />;
    return <Navigate to="/dashboard" />;
};

// Auth-only routes that need centered layout
const AUTH_ROUTES = ['/auth', '/login', '/'];

function AppRoutes() {
    const location = useLocation();
    const { user } = useAuth();

    // Auth pages (role selection, login) = centered; Dashboards = full width
    const isAuthPage =
        !user &&
        (AUTH_ROUTES.includes(location.pathname) ||
            location.pathname.startsWith('/auth'));
    const mainClass = isAuthPage ? 'auth-main' : 'dashboard-main';

    return (
        <div className="App">
            <div className="traffic-scene" aria-hidden="true">
                <span className="road-lines road-lines-left"></span>
                <span className="road-lines road-lines-right"></span>
                <span className="traffic-object traffic-light-shape"></span>
                <span className="traffic-object helmet-shape"></span>
                <span className="traffic-object sign-board-shape"></span>
                <span className="traffic-object cone-shape cone-one"></span>
                <span className="traffic-object cone-shape cone-two"></span>
            </div>
            <Navbar />
            <main className={mainClass}>
                <Routes>
                    {/* Public / Landing */}
                    <Route path="/" element={<HomeRedirect />} />

                    <Route path="/auth" element={<Auth />} />
                    <Route path="/login" element={<Navigate to="/auth" />} />

                    {/* Public Add Violation (Simulating Hardware Request) */}
                    <Route
                        path="/add-violation"
                        element={<Navigate to="/rto" replace />}
                    />
                    <Route
                        path="/unauthorized"
                        element={
                            <div className="workspace panel">
                                <h1>Access restricted</h1>
                                <p>Your account does not have access to this portal.</p>
                            </div>
                        }
                    />

                    {/* Profile Route - ALL ROLES */}
                    <Route
                        element={
                            <ProtectedRoute
                                allowedRoles={['USER', 'ADMIN', 'GOVT', 'RTO']}
                            />
                        }
                    >
                        <Route path="/profile" element={<UserProfile />} />
                        <Route path="/evidence/:id" element={<Evidence />} />
                        <Route path="/cases" element={<Casebook />} />
                        <Route path="/cases/:id" element={<CasePage />} />
                        <Route path="/guide" element={<ProjectGuide />} />
                    </Route>

                    {/* User Routes */}
                    <Route
                        element={
                            <ProtectedRoute allowedRoles={['USER', 'ADMIN', 'RTO']} />
                        }
                    >
                        <Route path="/dashboard" element={<UserDashboard />} />
                    </Route>

                    {/* RTO Routes */}
                    <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'RTO']} />}>
                        <Route path="/rto" element={<Overview />} />
                        <Route path="/operations" element={<RTODashboard />} />
                        <Route path="/datasets" element={<DatasetLibrary />} />
                        <Route path="/registry" element={<Registry />} />
                        <Route path="/monitor" element={<Monitor />} />
                        <Route path="/calibration" element={<Calibration />} />
                    </Route>

                    {/* Gov Routes */}
                    <Route
                        element={
                            <ProtectedRoute allowedRoles={['GOVT', 'ADMIN', 'RTO']} />
                        }
                    >
                        <Route path="/government" element={<GovernmentAnalytics />} />
                    </Route>
                    <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                        <Route path="/admin" element={<Admin />} />
                    </Route>
                    <Route
                        path="*"
                        element={
                            <div className="workspace panel">
                                <h1>Page not found</h1>
                                <a href="/">Return to your portal</a>
                            </div>
                        }
                    />
                </Routes>
            </main>
        </div>
    );
}

function App() {
    return (
        <ToastProvider>
            <AuthProvider>
                <Router>
                    <AppRoutes />
                </Router>
            </AuthProvider>
        </ToastProvider>
    );
}

export default App;
