import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { workflowClient } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermissions";

export default function WorkflowDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const permissions = usePermissions();
  const [workflow, setWorkflow] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWorkflow = async () => {
      try {
        const res = await workflowClient.get(`/workflows/${id}`);
        setWorkflow(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load workflow");
      } finally {
        setLoading(false);
      }
    };

    fetchWorkflow();
  }, [id]);

  const handleAction = async (action: 'approve' | 'reject') => {
    try {
      await workflowClient.post(`/workflows/${id}/${action}`);
      navigate('/workflows');
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError("Someone already handled this.");
      } else {
        setError(err.response?.data?.detail || `Failed to ${action} workflow`);
      }
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!workflow) return <div className="text-red-500">{error}</div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="bg-white shadow-sm border border-gray-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{workflow.title}</h2>
        <div className="flex items-center space-x-4 text-sm text-gray-500 mb-6">
          <span>Status: <span className="font-semibold capitalize">{workflow.status}</span></span>
          <span>Requester: {workflow.requester_name || "Unknown"}</span>
        </div>
        
        <div className="prose max-w-none text-gray-700 mb-8">
          <p>{workflow.description || "No description provided."}</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-600">
            {error}
          </div>
        )}

        {workflow.status === 'pending' && permissions.canApproveWorkflow && (
          <div className="flex space-x-4 border-t pt-4">
            <button
              onClick={() => handleAction('approve')}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium transition-colors"
            >
              Approve
            </button>
            <button
              onClick={() => handleAction('reject')}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium transition-colors"
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
