import axios, { AxiosInstance } from "axios";
import { logger } from "./logger";

// Helper to create clients with interceptors
function createApiClient(baseURL: string = ""): AxiosInstance {
  const client = axios.create({
    baseURL,
    headers: {
      "Content-Type": "application/json",
    },
  });

  client.interceptors.request.use(
    (config) => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      logger.debug("API Request", `${config.method?.toUpperCase()} ${config.baseURL || ''}${config.url}`, config.data ? { payload: config.data } : undefined);
      
      return config;
    },
    (error) => Promise.reject(error)
  );

  client.interceptors.response.use(
    (response) => {
      logger.debug("API Response", `${response.config.method?.toUpperCase()} ${response.baseURL || ''}${response.config.url} [${response.status}]`, { data: response.data });
      return response;
    },
    async (error) => {
      logger.error("API Error", `${error.config?.method?.toUpperCase()} ${error.config?.baseURL || ''}${error.config?.url} [${error.response?.status || 'Network Error'}]`, error.response?.data || error.message);
      const originalRequest = error.config;

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
          if (!refreshToken) {
            throw new Error("No refresh token");
          }

          // Use a raw axios call to avoid interceptor loops
          const refreshResponse = await axios.post(`/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const newAccessToken = refreshResponse.data.access_token;
          
          if (typeof window !== "undefined") {
            localStorage.setItem("access_token", newAccessToken);
          }

          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          logger.info("API Client", "Token refresh successful, retrying original request");
          return client(originalRequest);
        } catch (refreshError) {
          logger.warn("API Client", "Token refresh failed, logging out");
          if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
          return Promise.reject(refreshError);
        }
      }

      if (error.response?.status === 403) {
        logger.warn("API Client", "Permission denied (403)");
      } else if (error.response?.status === 409) {
        logger.info("API Client", "Conflict (409) - Already handled by UI typically");
      }

      return Promise.reject(error);
    }
  );

  return client;
}

// Export a dedicated client for each backend service
export const authClient = createApiClient("/auth");
export const tenantUserClient = createApiClient(""); // Handles /users and /invitations
export const workflowClient = createApiClient(""); // Handles /projects and /workflows
export const notificationClient = createApiClient("/notifications");
export const auditClient = createApiClient("/audit-logs");
