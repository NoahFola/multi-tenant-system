import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { authClient, tenantUserClient } from "@/lib/api-client";
import { logger } from "@/lib/logger";

interface User {
  id: string;
  email: string;
  role_id: string;
  status?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, refreshToken: string, userData: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const initAuth = async () => {
      logger.info("AuthProvider", "Initializing auth state...");
      const token = localStorage.getItem("access_token");
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          const userId = payload.sub;
          logger.debug("AuthProvider", `Found access token, verifying via /users/${userId}`);
          const res = await tenantUserClient.get(`/users/${userId}`);
          setUser(res.data);
          logger.info("AuthProvider", "User session restored", { user: res.data });
        } catch (error) {
          logger.warn("AuthProvider", "Failed to restore user session, clearing tokens", error);
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
      } else {
        logger.debug("AuthProvider", "No access token found during initialization");
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  useEffect(() => {
    if (!loading) {
      const isAuthRoute = ["/login", "/register", "/verify-email", "/forgot-password"].includes(location.pathname);
      
      if (!user && !isAuthRoute) {
        logger.info("AuthProvider", `Unauthenticated user accessing protected route ${location.pathname}, redirecting to /login`);
        navigate("/login");
      } else if (user && isAuthRoute) {
        logger.info("AuthProvider", `Authenticated user accessing auth route ${location.pathname}, redirecting to /`);
        navigate("/");
      }
    }
  }, [user, loading, location.pathname, navigate]);

  const login = (token: string, refreshToken: string, userData: User) => {
    logger.info("AuthProvider", "User logging in", { userId: userData.id, role_id: userData.role_id });
    localStorage.setItem("access_token", token);
    localStorage.setItem("refresh_token", refreshToken);
    setUser(userData);
    navigate("/");
  };

  const logout = async () => {
    logger.info("AuthProvider", "User logging out...");
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        await authClient.post("/logout", { refresh_token: refreshToken });
      } catch (e) {
        console.error("Logout failed on server:", e);
      }
    }
    logger.debug("AuthProvider", "Clearing local storage tokens and state");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    logger.info("AuthProvider", "Logout complete, redirecting to /login");
    navigate("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
