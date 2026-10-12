import { useEffect, useState } from "react";
import { notificationClient } from "@/lib/api-client";

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await notificationClient.get("");
        setNotifications(res.data);
      } catch (error) {
        console.error("Failed to fetch notifications", error);
      } finally {
        setLoading(false);
      }
    };
    fetchNotifications();
  }, []);

  const markAsRead = async (id: string) => {
    try {
      await notificationClient.post(`/${id}/read`);
      setNotifications(notifications.map((n: any) => n.id === id ? { ...n, read: true } : n));
    } catch (error) {
      console.error("Failed to mark as read", error);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Notifications</h1>

      <div className="bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading notifications...</div>
        ) : notifications.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No notifications.</div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {notifications.map((notification: any) => (
              <li key={notification.id} className={`p-4 hover:bg-gray-50 flex justify-between items-center ${notification.read ? 'opacity-75' : ''}`}>
                <div>
                  <p className={`text-sm ${notification.read ? 'text-gray-600' : 'font-medium text-gray-900'}`}>
                    {notification.message}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(notification.created_at).toLocaleString()}
                  </p>
                </div>
                {!notification.read && (
                  <button 
                    onClick={() => markAsRead(notification.id)}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium bg-blue-50 px-3 py-1 rounded-full"
                  >
                    Mark Read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
