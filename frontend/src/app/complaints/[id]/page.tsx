"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { PageHeader } from "@/components/layout/page-header";
import { DashboardSection } from "@/components/ui/dashboard-section";
import { StatusBadge } from "@/components/complaints/status-badge";
import { PriorityBadge } from "@/components/complaints/priority-badge";
import { AIAnalysisCard } from "@/components/complaints/ai-analysis-card";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { ComplaintAttachmentItem } from "@/components/complaints/complaint-attachment-item";
import { complaintsApi, ApiError } from "@/lib/api-client";
import { ComplaintDetailResponse, ComplaintPriority } from "@/types/complaint";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/context/auth-context";
import {
  ArrowLeft,
  Calendar,
  Clock,
  FileText,
  FileImage,
  ExternalLink,
  MapPin,
  ShieldCheck,
  Tag,
  History,
  Building,
  User,
  Paperclip,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export default function ComplaintDetailsPage() {
  const { user } = useAuth();
  const params = useParams();
  const router = useRouter();
  const complaintId = params?.id as string;

  const [complaint, setComplaint] = useState<ComplaintDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComplaintDetails = useCallback(async () => {
    if (!complaintId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await complaintsApi.getById(complaintId);
      setComplaint(data);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("The requested complaint could not be found.");
        } else if (err.status === 403) {
          setError("Access denied: You are not authorized to view this complaint.");
        } else {
          setError(err.message);
        }
      } else {
        setError(err?.message || "Failed to load complaint details.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [complaintId]);

  useEffect(() => {
    fetchComplaintDetails();
  }, [fetchComplaintDetails]);

  if (isLoading) {
    return (
      <DashboardLayout allowedRoles={["CITIZEN", "OFFICER", "ADMIN"]}>
        <div className="py-12">
          <LoadingState message="Retrieving grievance record and lifecycle timeline..." />
        </div>
      </DashboardLayout>
    );
  }

  if (error || !complaint) {
    return (
      <DashboardLayout allowedRoles={["CITIZEN", "OFFICER", "ADMIN"]}>
        <div className="mb-4">
          <Link
            href="/complaints"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to My Grievances
          </Link>
        </div>
        <ErrorState
          title="Grievance Details Unavailable"
          message={error || "Grievance record not found"}
          retry={fetchComplaintDetails}
        />
      </DashboardLayout>
    );
  }

  const categoryName = complaint.category?.name || "General Civic";

  return (
    <DashboardLayout allowedRoles={["CITIZEN", "OFFICER", "ADMIN"]}>
      {/* Back button */}
      <div className="mb-4 flex items-center justify-between">
        <Link
          href="/complaints"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to My Grievances
        </Link>
        <button
          onClick={fetchComplaintDetails}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md bg-white hover:bg-slate-50 transition-colors"
          title="Refresh complaint status"
        >
          <RefreshCw className="w-3 h-3" /> Refresh Status
        </button>
      </div>

      {/* Admin Notice Banner if viewer is Admin */}
      {user?.role?.name === "ADMIN" && (
        <div className="mb-4 p-3 rounded-lg border border-purple-200 bg-purple-50/70 flex items-center justify-between text-xs text-purple-900">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-purple-700 flex-shrink-0" />
            <span>You are viewing this complaint as Administrator.</span>
          </div>
          <Link
            href={`/admin/complaints/${complaint.id}`}
            className="font-semibold text-purple-700 hover:text-purple-900 inline-flex items-center gap-1 bg-white px-2.5 py-1 rounded border border-purple-200"
          >
            Manage in Admin Console &rarr;
          </Link>
        </div>
      )}

      {/* Header with Ticket ID and Status */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
              {complaint.ticket_number}
            </span>
            <StatusBadge status={complaint.status} />
            {complaint.priority && (
              <PriorityBadge priority={complaint.priority as ComplaintPriority} />
            )}
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-1.5">
            {complaint.title}
          </h1>
        </div>

        <div className="text-right text-xs text-slate-500 flex sm:flex-col items-center sm:items-end justify-between gap-1">
          <span>Submitted on</span>
          <span className="font-medium text-slate-800">
            {formatDate(complaint.created_at)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Issue Description Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-blue-600" />
              Detailed Grievance Description
            </h3>
            <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed bg-slate-50/70 p-4 rounded-lg border border-slate-100">
              {complaint.description}
            </p>
          </div>

          {/* Location & Geospatial Data Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-blue-600" />
              Geographic & Location Tagging
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Reported Landmark / Address</span>
                <span className="font-medium text-slate-900 mt-0.5 block">
                  {complaint.address || complaint.location_text || complaint.location || "Not specified"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">GPS Coordinates (WGS-84)</span>
                <span className="font-mono text-slate-900 mt-0.5 block">
                  {complaint.latitude?.toFixed(6)}, {complaint.longitude?.toFixed(6)}
                </span>
              </div>
            </div>
          </div>

          {/* Photographic Evidence & Attachments Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Paperclip className="w-4 h-4 text-blue-600" />
                Photographic & Media Evidence
              </h3>
              <span className="text-xs text-slate-500 font-medium">
                {complaint.attachments?.length || 0} file{complaint.attachments?.length !== 1 ? "s" : ""}
              </span>
            </div>

            {complaint.attachments && complaint.attachments.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {complaint.attachments.map((file) => (
                  <ComplaintAttachmentItem
                    key={file.id}
                    complaintId={complaint.id}
                    attachment={file}
                  />
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-lg">
                No photographic evidence was attached to this grievance report.
              </div>
            )}
          </div>

          {/* Audit Lifecycle Timeline / Status History */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <History className="w-4 h-4 text-blue-600" />
              Official Redressal Timeline & Status History
            </h3>

            {complaint.status_history && complaint.status_history.length > 0 ? (
              <div className="relative pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {complaint.status_history.map((log, index) => (
                  <div key={log.id} className="relative">
                    <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                    <div className="flex flex-wrap items-center justify-between gap-1 text-xs">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={log.new_status} />
                        {log.old_status && (
                          <span className="text-[11px] text-slate-400">
                            (from {log.old_status})
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {formatDate(log.created_at)}
                      </span>
                    </div>
                    {log.remarks && (
                      <p className="mt-1 text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                        {log.remarks}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-4 text-center text-slate-400 text-xs">
                No state transition history recorded yet.
              </div>
            )}
          </div>
        </div>

        {/* Sidebar / Metadata (1 col) */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 text-xs">
            <h4 className="font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-2">
              Ticket Metadata
            </h4>

            <div>
              <span className="text-slate-500 block">Municipal Category</span>
              <span className="font-semibold text-slate-900 mt-0.5 block">
                {categoryName}
              </span>
              {complaint.category?.default_sla_hours && (
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Resolution Target SLA: {complaint.category.default_sla_hours} hours
                </span>
              )}
            </div>

            <div>
              <span className="text-slate-500 block">Department Assignment</span>
              <span className="font-medium text-slate-700 mt-0.5 block">
                {complaint.assigned_officer?.badge_number
                  ? `Officer Badge: ${complaint.assigned_officer.badge_number}`
                  : "Pending Municipal Triage"}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Municipal Tracking ID</span>
              <span className="font-mono text-[11px] text-slate-600 break-all mt-0.5 block">
                {complaint.id}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block">Last Updated</span>
              <span className="text-slate-700 mt-0.5 block">
                {formatDate(complaint.updated_at)}
              </span>
            </div>

            {complaint.resolved_at && (
              <div>
                <span className="text-slate-500 block">Resolved At</span>
                <span className="text-emerald-700 font-medium mt-0.5 block">
                  {formatDate(complaint.resolved_at)}
                </span>
              </div>
            )}

            {complaint.closed_at && (
              <div>
                <span className="text-slate-500 block">Closed At</span>
                <span className="text-slate-700 font-medium mt-0.5 block">
                  {formatDate(complaint.closed_at)}
                </span>
              </div>
            )}
          </div>

          {/* AI Decision Support Card */}
          <AIAnalysisCard data={complaint.ai_analysis} />

          {/* Citizen Security Notice */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-500 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-blue-700 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-slate-700">Official Municipal Redressal</p>
              <p className="mt-0.5 text-slate-500">
                This record is protected by municipal RBAC and audit logging. Inquiries can quote ticket {complaint.ticket_number}.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
