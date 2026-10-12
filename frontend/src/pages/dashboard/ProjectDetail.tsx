import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { workflowClient } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermissions";
import { Plus } from "lucide-react";

export default function ProjectDetail() {
  const { id } = useParams();
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const permissions = usePermissions();

  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const res = await workflowClient.get(`/projects/${id}/workflows`);
        setWorkflows(res.data);
      } catch (error) {
        console.error("Failed to fetch workflows", error);
      } finally {
        setLoading(false);
      }
    };
    if (id) {
        fetchWorkflows();
    }
  }, [id]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Project Workflows</h1>
        {permissions.canApproveWorkflow && (
          <button className="flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">
            <Plus className="h-4 w-4 mr-2" />
            New Request
          </button>
        )}
      </div>

      <div className="bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Requester</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-gray-500">Loading workflows...</td>
              </tr>
            ) : workflows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-gray-500">No workflows found in this project.</td>
              </tr>
            ) : (
              workflows.map((workflow: any) => (
                <tr key={workflow.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {workflow.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      workflow.status === 'approved' ? 'bg-green-100 text-green-800' :
                      workflow.status === 'rejected' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {workflow.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {workflow.requester_name || 'System'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link to={`/workflows/${workflow.id}`} className="text-blue-600 hover:text-blue-900">
                      View
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
