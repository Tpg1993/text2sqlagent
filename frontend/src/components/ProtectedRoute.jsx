import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-950 text-slate-200">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </div>
        );
    }

    if (!user) {
        // Redirect to login, but save the current location to redirect back after login
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children;
}
