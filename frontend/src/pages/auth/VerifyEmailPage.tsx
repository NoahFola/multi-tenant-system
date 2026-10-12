import { useEffect, useState } from "react";
import { useLocation, Link, useSearchParams } from "react-router-dom";
import { authClient } from "@/lib/api-client";

export default function VerifyEmailPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const email = location.state?.email;
  const code = searchParams.get("code");
  
  const [status, setStatus] = useState<"pending" | "success" | "error">(code ? "pending" : "pending");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (code) {
      const verifyCode = async () => {
        try {
          const res = await authClient.get(`/verify-email?code=${code}`);
          setStatus("success");
          setMessage(res.data.message || "Email verified successfully!");
        } catch (error: any) {
          setStatus("error");
          setMessage(error.response?.data?.detail || "Invalid or expired verification code.");
        }
      };
      verifyCode();
    }
  }, [code]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-lg border border-gray-100 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Email Verification</h1>
        
        {!code ? (
          <div className="text-sm text-gray-600">
            We've sent a verification link to <span className="font-semibold text-gray-900">{email || "your email address"}</span>.
            Please click the link in the email to verify your account before logging in.
          </div>
        ) : status === "pending" ? (
          <div className="text-sm text-gray-600">Verifying your code...</div>
        ) : status === "success" ? (
          <div className="p-4 bg-green-50 text-green-700 rounded-md border border-green-200">
            {message}
          </div>
        ) : (
          <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
            {message}
          </div>
        )}

        <div className="pt-4">
          <Link to="/login" className="text-blue-600 font-medium hover:underline">
            Return to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
