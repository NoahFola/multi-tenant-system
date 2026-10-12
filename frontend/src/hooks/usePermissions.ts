import { useAuth } from "@/components/providers/AuthProvider";

export const usePermissions = () => {
  const { user } = useAuth();
  
  const role = user?.role?.toLowerCase() || "";

  return {
    isAdmin: role === "admin",
    isManager: role === "manager" || role === "admin",
    canApproveWorkflow: role === "manager" || role === "admin",
    canManageUsers: role === "admin",
    canViewAuditLogs: role === "admin",
  };
};
