import { useEffect, useState } from "react";
import { workflowClient } from "@/lib/api-client";

export default function Dashboard() {
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await workflowClient.get("/workflows");
        const workflows = res.data;
        const pending = workflows.filter((w: any) => w.status === "pending").length;
        const approved = workflows.filter((w: any) => w.status === "approved").length;
        const rejected = workflows.filter((w: any) => w.status === "rejected").length;
        
        setStats({ pending, approved, rejected });
      } catch (error) {
        console.error("Failed to fetch dashboard stats", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
      
      {loading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 h-32 bg-gray-200 rounded-lg"></div>
          <div className="flex-1 h-32 bg-gray-200 rounded-lg"></div>
          <div className="flex-1 h-32 bg-gray-200 rounded-lg"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
            <h3 className="text-sm font-medium text-gray-500">Pending Requests</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{stats.pending}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
            <h3 className="text-sm font-medium text-gray-500">Approved</h3>
            <p className="text-3xl font-bold text-green-600 mt-2">{stats.approved}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
            <h3 className="text-sm font-medium text-gray-500">Rejected</h3>
            <p className="text-3xl font-bold text-red-600 mt-2">{stats.rejected}</p>
          </div>
        </div>
      )}
    </div>
  );
}
